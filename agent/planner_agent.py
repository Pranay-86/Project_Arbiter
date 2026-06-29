import json
import re
from agent.prompts import SYSTEM_PROMPT_TOOLS
from core.logger import get_logger

logger = get_logger("planner_agent")

_KNOWN_PAPERS = {
    "attention is all you need":    "https://arxiv.org/pdf/1706.03762",
    "bert":                         "https://arxiv.org/pdf/1810.04805",
    "gpt-3":                        "https://arxiv.org/pdf/2005.14165",
    "resnet":                       "https://arxiv.org/pdf/1512.03385",
    "deep residual learning":       "https://arxiv.org/pdf/1512.03385",
    "generative adversarial":       "https://arxiv.org/pdf/1406.2661",
    "language models are few shot": "https://arxiv.org/pdf/2005.14165",
}


class PlannerAgent:

    def __init__(self, llm, registry, knowledge):
        self.llm      = llm
        self.registry = registry
        self.knowledge = knowledge

    def propose(self, state) -> list:
        """
        Propose next actions using the ReasoningResult attached to state.
        The planner works from reasoned intent, not raw user input.
        """
        reasoning = getattr(state, "reasoning", None)

        # --- Use first_action from Reasoner if available and not yet tried ---
        if reasoning and reasoning.first_action and not state.tool_history:
            action = reasoning.first_action
            tool   = action.get("action", "")
            if tool and self.registry.get_tool(tool):
                logger.info("Planner: using Reasoner's first_action: %s", action)
                return [action]

        # --- Short-circuit: known paper URL ---
        if reasoning:
            paper_url = self._lookup_known_paper(reasoning.true_intent)
            if not paper_url:
                paper_url = self._lookup_known_paper(state.user_request)
        else:
            paper_url = self._lookup_known_paper(state.user_request)

        if paper_url and "download_paper" not in state.tool_history:
            logger.info("Planner: known paper shortcut → %s", paper_url)
            return [{"action": "download_paper", "parameters": {"url": paper_url}}]

        # --- Short-circuit: extract PDF from last search result ---
        shortcut = self._maybe_download_from_last_obs(state)
        if shortcut:
            return shortcut

        # --- Ask LLM with full reasoning context ---
        tools      = self.registry.list_tools()
        recent_obs = self._safe_obs(state)
        failed     = {o.get("tool") for o in state.observations if o.get("status") == "error"}

        reasoning_context = reasoning.to_context_string() if reasoning else f"User request: {state.user_request}"

        prompt = (
            f"{SYSTEM_PROMPT_TOOLS}\n\n"
            "You are a planning agent. Use the reasoning below to decide the NEXT action.\n\n"
            f"=== REASONING ===\n{reasoning_context}\n=================\n\n"
            "Rules:\n"
            "- Follow the planned tool sequence from the reasoning\n"
            "- If a tool failed, skip it and use the next in sequence\n"
            "- Use EXACT parameter names as shown in the tool list\n"
            "- Use resolved entity values (e.g. corrected app names, URLs)\n"
            "- Never repeat a failed tool\n\n"
            f"Available tools: {tools}\n"
            f"Failed tools: {list(failed)}\n"
            f"Tool history: {state.tool_history}\n"
            f"Recent observations:\n{json.dumps(recent_obs, indent=2)}\n\n"
            "Return a JSON array of 1-2 next actions ONLY."
        )

        response  = self.llm.chat(prompt)
        candidates = self._parse_candidates(response)

        valid = [
            c for c in candidates
            if isinstance(c, dict)
            and isinstance(c.get("action"), str)
            and not isinstance(c.get("action"), dict)
        ]

        valid = self._filter_bad_downloads(valid)

        if not valid:
            logger.warning("Planner: parse failed, using smart fallback")
            return self._smart_fallback(state, failed, reasoning)

        return valid

    # ------------------------------------------------------------------ #

    def _lookup_known_paper(self, text: str) -> str:
        text_lower = (text or "").lower()
        for keyword, url in _KNOWN_PAPERS.items():
            if keyword in text_lower:
                return url
        return ""

    def _maybe_download_from_last_obs(self, state) -> list:
        if not state.observations:
            return []
        last = state.get_last_observation()
        if last["status"] != "success":
            return []
        if last.get("tool") not in ("search_arxiv", "search_web"):
            return []
        if "download_paper" in state.tool_history or "download_file" in state.tool_history:
            return []

        combined = ((state.goal or "") + " " + state.user_request).lower()
        if not any(w in combined for w in ("download", "get", "fetch", "paper", "save", "pdf")):
            return []

        data    = last.get("data", [])
        pdf_url = self._extract_best_pdf_url(data) if isinstance(data, list) else ""
        if pdf_url:
            return [{"action": "download_paper", "parameters": {"url": pdf_url}}]
        return []

    def _extract_best_pdf_url(self, results: list) -> str:
        for r in results:
            link = r.get("link", "") if isinstance(r, dict) else ""
            if "arxiv.org/pdf" in link:
                return link
        for r in results:
            link = r.get("link", "") if isinstance(r, dict) else ""
            if link.lower().endswith(".pdf"):
                return link
        for r in results:
            link = r.get("link", "") if isinstance(r, dict) else ""
            if "arxiv.org/abs/" in link:
                return link.replace("/abs/", "/pdf/")
        return ""

    def _filter_bad_downloads(self, candidates: list) -> list:
        filtered = []
        for c in candidates:
            if c.get("action") in ("download_paper", "download_file"):
                url = (c.get("parameters") or {}).get("url", "").strip()
                if not url:
                    logger.warning("Planner: dropping download with empty URL")
                    continue
            filtered.append(c)
        return filtered

    def _smart_fallback(self, state, failed: set, reasoning) -> list:
        # Try to get URL from any past successful search
        for obs in reversed(state.observations):
            if obs.get("status") == "success" and isinstance(obs.get("data"), list):
                url = self._extract_best_pdf_url(obs["data"])
                if url:
                    return [{"action": "download_paper", "parameters": {"url": url}}]

        if "search_arxiv" not in failed and "search_arxiv" not in state.tool_history:
            query = (reasoning.corrected_input if reasoning else state.user_request)
            return [{"action": "search_arxiv", "parameters": {"query": query}}]

        if "search_web" not in failed:
            query = (reasoning.true_intent if reasoning else state.user_request) + " arxiv pdf"
            return [{"action": "search_web", "parameters": {"query": query}}]

        return [{"action": "final_answer",
                 "parameters": {"answer": "I was unable to complete this task after multiple attempts."}}]

    def _safe_obs(self, state) -> list:
        result = []
        for obs in state.observations[-2:]:
            safe = dict(obs)
            if len(str(safe.get("data", ""))) > 400:
                safe["data"] = str(safe["data"])[:400] + "...(truncated)"
            result.append(safe)
        return result

    def _parse_candidates(self, text: str) -> list:
        clean = re.sub(r"```(?:json)?", "", text).strip().strip("`").strip()
        try:
            data = json.loads(clean)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "action" in data:
                return [data]
        except (json.JSONDecodeError, ValueError):
            pass
        match = re.search(r"\[[\s\S]*?\]", clean)
        if match:
            try:
                data = json.loads(match.group())
                if isinstance(data, list):
                    return data
            except (json.JSONDecodeError, ValueError):
                pass
        match = re.search(r"\{[\s\S]*?\}", clean)
        if match:
            try:
                data = json.loads(match.group())
                if isinstance(data, dict) and "action" in data:
                    return [data]
            except (json.JSONDecodeError, ValueError):
                pass
        return []

import json
import re
import os
import time
from config.config_loader import cfg
from core.task_state import TaskState
from core.logger import get_logger
from tools.executor import ToolExecutor
from agent.intent_router import IntentRouter
from core.action_validator import ActionValidator
from agent.reflection_engine import ReflectionEngine
from agent.planner_agent import PlannerAgent
from agent.critic_agent import CriticAgent
from agent.reasoner import Reasoner
from memory.vector_store import VectorStore
from memory.knowledge_engine import KnowledgeEngine
from memory.conversation_memory import ConversationMemory
from agent.prompts import SYSTEM_PROMPT_CHAT, SYSTEM_PROMPT_SEQUENCE
from agent.tool_prompt_builder import build_tool_prompt

logger = get_logger("agent_loop")

_DESKTOP  = os.path.join(os.path.expanduser("~"), "Desktop")
_USERNAME = os.environ.get("USERNAME") or os.environ.get("USER") or "User"
_HOME     = os.path.expanduser("~")


class AgentLoop:

    def __init__(self, llm, registry):
        self.llm       = llm
        self.registry  = registry
        self.max_steps = cfg.get("agent.max_steps", 15)

        self.tool_executor = ToolExecutor(registry)
        self.vector_store  = VectorStore()
        self.knowledge     = KnowledgeEngine(llm, self.vector_store)
        self.memory        = ConversationMemory()

        self.reasoner  = Reasoner(llm, registry)
        self.planner   = PlannerAgent(llm, registry, self.knowledge)
        self.critic    = CriticAgent(llm)
        self.validator = ActionValidator(registry)
        self.router    = IntentRouter()
        self.reflector = ReflectionEngine()

        self._last_task_result = None
        self._last_task_input  = None

    # ------------------------------------------------------------------ #
    #  Path resolution                                                     #
    # ------------------------------------------------------------------ #

    def _resolve_paths(self, actions: list) -> list:
        replacements = {
            "DESKTOP_PATH": _DESKTOP,
            "DESKTOP":      _DESKTOP,
            "~/Desktop":    _DESKTOP,
            "~/desktop":    _DESKTOP,
            "HOME":         _HOME,
            "~":            _HOME,
            "USERNAME":     _USERNAME,
        }
        resolved = []
        for action in actions:
            params = dict(action.get("parameters", {}) or {})
            for key, value in params.items():
                if isinstance(value, str):
                    for placeholder, real in replacements.items():
                        value = value.replace(placeholder, real)
                    params[key] = value
            resolved.append({**action, "parameters": params})
        return resolved

    # ------------------------------------------------------------------ #
    #  Action sanitiser                                                    #
    # ------------------------------------------------------------------ #

    def _sanitise_actions(self, actions: list) -> list:
        """
        Hard rule: if write_file is in the sequence, remove open_application.
        Opening a blank app then writing to disk separately is confusing —
        the user sees an empty window and thinks nothing happened.
        write_file + open_file is the correct pattern.
        """
        tool_names = [a.get("action", "") for a in actions]

        has_write_file = "write_file" in tool_names
        has_open_app   = "open_application" in tool_names

        if has_write_file and has_open_app:
            before = [a.get("action") for a in actions]
            actions = [a for a in actions if a.get("action") != "open_application"]
            after   = [a.get("action") for a in actions]
            logger.info(
                "Sanitiser: removed open_application (write_file present). "
                "%s → %s", before, after
            )

        # Also remove type_text steps that look like save-dialog inputs
        # (contain path-like strings with slashes and dots)
        sanitised = []
        for action in actions:
            if action.get("action") == "type_text":
                text = (action.get("parameters") or {}).get("text", "")
                if text and ("/" in text or "\\" in text) and "." in text:
                    logger.warning(
                        "Sanitiser: removed type_text with path-like text: '%s'", text
                    )
                    continue
            sanitised.append(action)

        return sanitised

    # ------------------------------------------------------------------ #
    #  Task classifier                                                     #
    # ------------------------------------------------------------------ #

    def _classify_task(self, user_input: str) -> str:
        lower = user_input.lower()

        research_signals = [
            "download", "search for", "find the", "look up",
            "paper", "arxiv", "youtube", "website", "url",
            "latest", "recent", "news", "link for", "link to",
            "give me the link", "get the link",
        ]
        sequence_signals = [
            " and ", " then ", "after that", "also ",
            "type", "write into", "save it", "save the file",
            "save on", "save to", "run it", "run the",
            "execute it", "click", "press", "create a file",
            "write a file", "write a script", "write code",
            "make a file", "make a script",
        ]

        if any(s in lower for s in research_signals):
            return "research"
        if any(s in lower for s in sequence_signals):
            return "sequence"
        return "single"

    # ------------------------------------------------------------------ #
    #  Sequence planner                                                    #
    # ------------------------------------------------------------------ #

    def _plan_sequence(self, user_input: str, memory_context: str) -> list:
        tool_desc = self.registry.get_tool_descriptions()
        tool_text = build_tool_prompt(tool_desc)

        system_context = (
            f"System paths (use these EXACT values):\n"
            f"  Desktop:  {_DESKTOP}\n"
            f"  Home:     {_HOME}\n"
            f"  Username: {_USERNAME}\n"
        )

        prompt = (
            f"{SYSTEM_PROMPT_SEQUENCE}\n\n"
            f"{system_context}\n"
            f"{tool_text}\n"
            f"Past context:\n{memory_context or 'none'}\n\n"
            f"User request: \"{user_input}\"\n\n"
            "Return ONLY a JSON array of actions."
        )

        response = self.llm.chat(prompt)
        actions  = self._parse_action_list(response)
        actions  = self._resolve_paths(actions)
        actions  = self._sanitise_actions(actions)
        return actions

    def _parse_action_list(self, text: str) -> list:
        clean = re.sub(r"<think>[\s\S]*?</think>", "", text).strip()
        clean = re.sub(r"```(?:json)?", "", clean).strip().strip("`").strip()

        try:
            data = json.loads(clean)
            if isinstance(data, list):
                return [a for a in data if isinstance(a, dict) and "action" in a]
            if isinstance(data, dict) and "action" in data:
                return [data]
        except (json.JSONDecodeError, ValueError):
            pass

        match = re.search(r"\[[\s\S]*\]", clean)
        if match:
            try:
                data = json.loads(match.group())
                if isinstance(data, list):
                    return [a for a in data if isinstance(a, dict) and "action" in a]
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

    # ------------------------------------------------------------------ #
    #  Execute sequence                                                    #
    # ------------------------------------------------------------------ #

    def _execute_sequence(self, actions: list, user_input: str) -> str:
        if not actions:
            return "No actions were planned."

        results   = []
        last_data = None
        last_tool = ""

        for i, action in enumerate(actions):
            tool   = action.get("action", "")
            params = action.get("parameters", {}) or {}

            # Pure delay step
            if tool == "type_text":
                delay  = float(params.get("delay", 0))
                text   = params.get("text", "")
                hotkey = params.get("hotkey", "")
                if delay > 0 and not text and not hotkey:
                    logger.info("Step %d | delay %.1fs", i, delay)
                    time.sleep(delay)
                    continue

            ok, corrected, err = self.validator.validate(action)
            if not ok:
                logger.warning("Step %d skipped (%s): %s", i, tool, err)
                continue

            tool   = corrected["action"]
            params = corrected.get("parameters", {})
            logger.info("Step %d | %s | %s", i, tool, params)

            result = self.tool_executor.execute(tool, params)

            if result["status"] == "success":
                data      = result.get("data")
                last_data = data
                last_tool = tool
                formatted = self._format_output(data, tool)
                results.append((True, tool, formatted))
            else:
                err_msg = result.get("error", "Unknown error")
                logger.warning("Step %d error (%s): %s", i, tool, err_msg)
                results.append((False, tool, f"✗ {err_msg}"))

        if not results:
            return "All steps failed or were skipped."

        if last_data is not None:
            self._last_task_result = last_data
            self._last_task_input  = user_input

        successes = [(t, r) for ok, t, r in results if ok]
        failures  = [(t, r) for ok, t, r in results if not ok]

        if successes:
            final = successes[-1][1]
            if final == "✓ Done." and len(successes) > 1:
                for _, r in reversed(successes):
                    if r != "✓ Done.":
                        final = r
                        break
            if failures:
                return f"{final} ({len(failures)} step(s) had errors — check logs)"
            return final

        return "\n".join(r for _, _, r in results)

    # ------------------------------------------------------------------ #
    #  Output formatting                                                   #
    # ------------------------------------------------------------------ #

    def _format_output(self, data, tool: str = "") -> str:
        if data is None:
            return "Done."
        if isinstance(data, dict):
            s = data.get("status", "")
            if s == "downloaded":
                return f"✓ Downloaded: {data.get('file', data.get('path', ''))}"
            if s == "written":
                return f"✓ Saved: {data.get('path', '')}"
            if s == "appended":
                return f"✓ Appended: {data.get('path', '')}"
            if s in ("copied", "moved"):
                return f"✓ {s.capitalize()}: {data.get('destination', '')}"
            if s == "deleted":
                return f"✓ Deleted: {data.get('path', '')}"
            if s == "created":
                return f"✓ Created: {data.get('path', '')}"
            if s == "opened":
                return f"✓ Opened: {data.get('path', '')}"
            if s == "error":
                return f"✗ {data.get('message', 'Error')}"
            if s == "success" or tool in (
                "open_application", "close_application",
                "type_text", "mouse_click", "notify",
            ):
                r = data.get("result", "")
                return f"✓ {r}" if r else "✓ Done."
            if "stdout" in data:
                out = data["stdout"].strip()
                return out if out else "Executed (no output)."
            if "file" in data:
                return f"✓ File: {data['file']}"
            if "path" in data:
                return f"✓ Path: {data['path']}"
            if "content" in data:
                return data["content"]
            if "matches" in data:
                m = data["matches"]
                return "\n".join(f"• {x}" for x in m[:20]) if m else "No files found."
            if "parameters" in data:
                p = data["parameters"]
                return p.get("answer") or p.get("message") or json.dumps(data, indent=2)
            return json.dumps(data, indent=2)

        if isinstance(data, list):
            lines = []
            for item in data[:8]:
                if isinstance(item, dict):
                    title = item.get("title", "")
                    link  = item.get("link", "") or item.get("url", "")
                    lines.append(f"• {title}\n  {link}" if link else f"• {title}")
                else:
                    lines.append(f"• {item}")
            return "\n".join(lines)

        if isinstance(data, str):
            try:
                parsed = json.loads(data)
                if isinstance(parsed, dict) and "parameters" in parsed:
                    p = parsed["parameters"]
                    return p.get("answer") or p.get("message") or data
            except (json.JSONDecodeError, TypeError):
                pass
            return data

        return str(data)

    def _get_memory_context(self, user_input: str) -> str:
        try:
            k = cfg.get("memory.retrieval_k", 3)
            return "\n".join(self.memory.retrieve(user_input, k=k))
        except Exception as exc:
            logger.warning("Memory retrieval failed: %s", exc)
            return ""

    # ------------------------------------------------------------------ #
    #  Chat mode                                                           #
    # ------------------------------------------------------------------ #

    def handle_chat(self, user_input: str) -> str:
        memory_context = self._get_memory_context(user_input)

        task_context = ""
        if self._last_task_result is not None:
            task_context = (
                f"\nPrevious task: {self._last_task_input}\n"
                f"Result: {self._format_output(self._last_task_result)}\n"
            )

        prompt = (
            f"{SYSTEM_PROMPT_CHAT}\n\n"
            f"Past Context:\n{memory_context}\n"
            f"{task_context}\n"
            f"User: {user_input}\n\n"
            "Respond naturally and helpfully."
        )

        response = self.llm.chat(prompt)
        self.memory.add(user_input, response)
        return self._format_output(response)

    # ------------------------------------------------------------------ #
    #  Sequence path                                                       #
    # ------------------------------------------------------------------ #

    def handle_sequence(self, user_input: str) -> str:
        memory_context = self._get_memory_context(user_input)
        logger.info("Sequence path: %s", user_input)

        actions = self._plan_sequence(user_input, memory_context)

        if not actions:
            logger.warning("No actions planned — falling back to research")
            return self.handle_research(user_input)

        logger.info("Planned %d actions: %s",
                    len(actions), [a.get("action") for a in actions])

        result = self._execute_sequence(actions, user_input)
        self.memory.add(user_input, result)
        return result

    # ------------------------------------------------------------------ #
    #  Research path                                                       #
    # ------------------------------------------------------------------ #

    def handle_research(self, user_input: str) -> str:
        memory_context = self._get_memory_context(user_input)
        logger.info("Research path: %s", user_input)

        reasoning = self.reasoner.reason(user_input, context=memory_context)
        logger.info("Intent: %s | Sequence: %s",
                    reasoning.true_intent, reasoning.tool_sequence)

        state = TaskState(user_request=reasoning.corrected_input or user_input)
        state.conversation_context = memory_context
        state.set_reasoning(reasoning)
        state.set_goal(reasoning.true_intent, ["non-empty result"])

        while state.steps_taken < self.max_steps:

            candidates = self.planner.propose(state)
            valid = []
            for action in candidates:
                ok, corrected, err = self.validator.validate(action)
                if ok:
                    valid.append(corrected)
                else:
                    logger.debug("Dropped: %s — %s", action, err)

            if not valid:
                return "I couldn't determine a valid action. Please try rephrasing."

            action = self.critic.evaluate(state, valid)
            tool   = action["action"]
            params = action.get("parameters", {})
            logger.info("Step %d | %s | %s", state.steps_taken, tool, params)

            result = self.tool_executor.execute(tool, params)
            state.add_tool_call(tool)
            state.add_observation(result)

            decision = self.reflector.evaluate(state)
            state.add_reflection(decision)
            logger.info("Decision: %s", decision)

            if decision == "COMPLETE":
                output = result.get("data")
                self._last_task_result = output
                self._last_task_input  = user_input
                formatted = self._format_output(output, tool)
                self.memory.add(user_input, formatted)
                return formatted

            if decision == "FAIL":
                output = result.get("data")
                if output:
                    return self._format_output(output, tool)
                self.memory.add(user_input, "Task failed")
                return "Task failed. Check logs/arbiter.log for details."

            state.increment_step()

        return f"Reached max steps ({self.max_steps})."

    # ------------------------------------------------------------------ #
    #  Entry point                                                         #
    # ------------------------------------------------------------------ #

    def run(self, user_input: str) -> str:
        if not self.router.requires_tool(user_input):
            return self.handle_chat(user_input)

        task_type = self._classify_task(user_input)
        logger.info("Task type: %s | input: %s", task_type, user_input)

        if task_type == "research":
            return self.handle_research(user_input)
        else:
            return self.handle_sequence(user_input)

import json
import re
from agent.prompts import SYSTEM_PROMPT_REASONING
from config.config_loader import cfg
from core.logger import get_logger

logger = get_logger("reasoner")


class Reasoner:
    """
    The thinking layer. Runs before the planner on every task.
    Uses chain-of-thought prompting to deeply understand intent
    before producing a structured execution plan.
    """

    def __init__(self, llm, registry):
        self.llm      = llm
        self.registry = registry

    def reason(self, user_input: str, context: str = "") -> "ReasoningResult":
        tools  = self._build_tool_summary()
        result = self._call_llm(user_input, context, tools)

        if not self._intent_matches_input(result, user_input):
            logger.warning(
                "Reasoner mismatch: got '%s' for input '%s'. Retrying.",
                result.true_intent, user_input
            )
            result = self._call_llm(user_input, context, tools, strict=True)

        logger.info(
            "Reasoner | input='%s' | intent='%s' | tools=%s | entities=%s",
            user_input, result.true_intent, result.tool_sequence, result.entities
        )
        return result

    # ------------------------------------------------------------------ #

    def _call_llm(self, user_input: str, context: str,
                  tools: str, strict: bool = False) -> "ReasoningResult":

        strict_block = (
            f"\nCRITICAL: You MUST reason about ONLY this message: \"{user_input}\"\n"
            "Ignore all past context. Your intent MUST match this exact input.\n"
        ) if strict else ""

        prompt = (
            f"{SYSTEM_PROMPT_REASONING}\n\n"
            "━━━ CURRENT USER MESSAGE ━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f'"{user_input}"\n'
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{strict_block}\n"
            f"Available tools:\n{tools}\n\n"
            "Past context (reference only):\n"
            f"{context or 'none'}\n\n"
            "Now reason through all 4 steps, then output the JSON."
        )

        response = self.llm.chat(prompt)

        # Strip <think>...</think> blocks — some models output these literally
        response = re.sub(r"<think>[\s\S]*?</think>", "", response).strip()

        return self._parse(response, user_input)

    # ------------------------------------------------------------------ #

    def _intent_matches_input(self, result: "ReasoningResult", user_input: str) -> bool:
        stopwords = {
            "can", "you", "please", "i", "want", "to", "the", "a", "an",
            "open", "me", "my", "could", "would", "hey", "for", "on",
            "get", "give", "find", "show", "provide", "what", "is", "are",
            "its", "their", "latest", "new", "some", "this", "that"
        }
        input_words = {
            w.lower().strip("?!.,\"'") for w in user_input.split()
            if w.lower().strip("?!.,\"'") not in stopwords and len(w) > 2
        }

        if not input_words:
            return True

        intent_text = (
            result.true_intent.lower() + " " +
            result.corrected_input.lower() + " " +
            " ".join(str(v).lower() for v in result.entities.values())
        )

        matches     = sum(1 for w in input_words if w in intent_text)
        match_ratio = matches / len(input_words)

        logger.debug("Intent match: words=%s ratio=%.2f", input_words, match_ratio)
        return match_ratio >= 0.25

    def _build_tool_summary(self) -> str:
        lines = []
        for tool in self.registry.get_tools():
            params = ", ".join(
                f"{k} ({v.split()[0]})"
                for k, v in getattr(tool, "parameters", {}).items()
            )
            desc = getattr(tool, "description", "")[:100]
            lines.append(f"  {tool.name}({params}) — {desc}")
        return "\n".join(lines)

    def _parse(self, text: str, original: str) -> "ReasoningResult":
        clean = re.sub(r"```(?:json)?", "", text).strip().strip("`").strip()
        data  = {}
        try:
            data = json.loads(clean)
        except (json.JSONDecodeError, ValueError):
            match = re.search(r"\{[\s\S]*\}", clean)
            if match:
                try:
                    data = json.loads(match.group())
                except (json.JSONDecodeError, ValueError):
                    pass

        return ReasoningResult(
            true_intent     = data.get("true_intent",     original),
            corrected_input = data.get("corrected_input", original),
            entities        = data.get("entities",        {}),
            tool_sequence   = data.get("tool_sequence",   []),
            first_action    = data.get("first_action",    None),
            reasoning       = data.get("reasoning",       ""),
            ambiguities     = data.get("ambiguities",     []),
            raw_input       = original,
        )


class ReasoningResult:

    def __init__(self, true_intent, corrected_input, entities,
                 tool_sequence, first_action, reasoning, ambiguities, raw_input):
        self.true_intent     = true_intent
        self.corrected_input = corrected_input
        self.entities        = entities
        self.tool_sequence   = tool_sequence
        self.first_action    = first_action
        self.reasoning       = reasoning
        self.ambiguities     = ambiguities
        self.raw_input       = raw_input

    def to_context_string(self) -> str:
        lines = [f"Intent: {self.true_intent}"]
        if self.corrected_input != self.raw_input:
            lines.append(f"Corrected: {self.corrected_input}")
        if self.entities:
            lines.append(f"Entities: {self.entities}")
        if self.tool_sequence:
            lines.append(f"Tool sequence: {' → '.join(self.tool_sequence)}")
        if self.reasoning:
            lines.append(f"Reasoning: {self.reasoning}")
        return "\n".join(lines)

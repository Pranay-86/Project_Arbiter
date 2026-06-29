import json
from agent.prompts import SYSTEM_PROMPT_TOOLS
from core.logger import get_logger

logger = get_logger("goal_generator")


class GoalGenerator:

    def __init__(self, llm):
        self.llm = llm

    def generate(self, user_request: str):
        """
        Returns (goal: str, success_criteria: list[str]).
        Falls back gracefully on LLM / parse failure.
        """
        prompt = (
            f"{SYSTEM_PROMPT_TOOLS}\n\n"
            "Convert the user request into a structured goal.\n\n"
            "Return JSON ONLY:\n"
            '{\n'
            '  "goal": "...",\n'
            '  "success_criteria": ["...", "..."]\n'
            '}\n\n'
            f"User request:\n{user_request}"
        )

        response = self.llm.chat(prompt)

        try:
            clean = response.strip().strip("```json").strip("```").strip()
            data = json.loads(clean)
            goal = data.get("goal", user_request)
            criteria = data.get("success_criteria", ["non-empty result"])
            return goal, criteria
        except Exception:
            logger.warning("GoalGenerator parse failed — using raw request as goal.")
            return user_request, ["non-empty result"]

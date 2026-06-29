import json
from agent.prompts import SYSTEM_PROMPT_TOOLS
from agent.action_scorer import ActionScorer
from core.logger import get_logger

logger = get_logger("critic_agent")


class CriticAgent:
    """
    Evaluates candidate actions and selects the best one.
    Uses LLM scoring with a heuristic ActionScorer as tiebreaker/fallback.
    """

    def __init__(self, llm):
        self.llm = llm
        self.scorer = ActionScorer()

    def evaluate(self, state, candidates: list) -> dict:
        if not candidates:
            return {"action": "final_answer", "parameters": {"answer": "No candidates."}}

        if len(candidates) == 1:
            return candidates[0]

        prompt = (
            f"{SYSTEM_PROMPT_TOOLS}\n\n"
            "You are a critic agent.\n\n"
            "Evaluate the candidate actions and select the BEST one.\n\n"
            "Return JSON ONLY:\n"
            '{"best_index": 0}\n\n'
            f"Candidates:\n{json.dumps(candidates, indent=2)}\n\n"
            f"Goal: {state.goal}\n"
            f"Recent Observations: {state.observations[-3:]}\n"
            f"Reflection History: {state.reflection_history[-3:]}\n\n"
            "Rules:\n"
            "- Avoid repeating failed tools\n"
            "- Prefer actions that directly advance the goal\n"
            "- Avoid redundant actions"
        )

        response = self.llm.chat(prompt)

        try:
            clean = response.strip().strip("```json").strip("```").strip()
            data = json.loads(clean)
            idx = int(data.get("best_index", 0))
            if 0 <= idx < len(candidates):
                return candidates[idx]
        except Exception:
            logger.warning("CriticAgent parse failed — using heuristic scorer.")

        # Heuristic fallback
        return self.scorer.select_best(state, candidates) or candidates[0]

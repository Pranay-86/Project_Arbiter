class ActionScorer:
    """
    Heuristic scorer for candidate actions.
    Used as a fallback when the CriticAgent LLM call fails.
    """

    def score(self, state, action: dict) -> float:
        tool = action.get("action")
        if not tool:
            return -999.0

        score = 0.0

        # Penalise repeated use of the same tool
        use_count = state.tool_history.count(tool)
        score -= use_count * 1.5

        # Penalise known failures for this tool
        failures = sum(
            1 for obs in state.observations
            if obs.get("tool") == tool and obs.get("status") == "error"
        )
        score -= failures * 3.0

        # Reward exploring a new tool
        if tool not in state.tool_history:
            score += 3.0

        # Reward momentum when things are going well
        if state.last_decision == "CONTINUE":
            score += 1.0

        return score

    def select_best(self, state, candidates: list) -> dict | None:
        if not candidates:
            return None
        return max(candidates, key=lambda a: self.score(state, a))

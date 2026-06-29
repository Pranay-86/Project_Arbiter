from config.config_loader import cfg
from core.logger import get_logger

logger = get_logger("reflection_engine")

_SEARCH_TOOLS   = {"search_web", "search_arxiv", "read_webpage", "list_files", "system_info"}
_TERMINAL_TOOLS = {"download_paper", "download_file", "write_file",
                   "run_python", "open_application", "final_answer"}


class ReflectionEngine:
    """
    Evaluates task state after each tool call and decides what to do next.
    Returns one of: COMPLETE | CONTINUE | RETRY | FAIL
    """

    def __init__(self):
        self.retry_limit = cfg.get("agent.retry_limit", 2)
        self.loop_window = cfg.get("agent.loop_detection_window", 3)

    def evaluate(self, state) -> str:
        if not state.observations:
            return "CONTINUE"

        last = state.get_last_observation()

        if last["status"] == "error":
            return self._handle_failure(state, last)

        if self._goal_satisfied(state):
            return "COMPLETE"

        if self._is_looping(state):
            logger.warning("Loop detected: %s", state.tool_history[-self.loop_window:])
            return "FAIL"

        return "CONTINUE"

    # ------------------------------------------------------------------ #

    def _handle_failure(self, state, last_obs: dict) -> str:
        """
        Count failures per-tool so one bad tool doesn't burn the global retry limit.
        Only FAIL if the SAME tool has failed retry_limit times in a row,
        or if ALL tools tried have failed.
        """
        failed_tool = last_obs.get("tool", "")

        # Count consecutive failures of this specific tool
        consecutive = 0
        for obs in reversed(state.observations):
            if obs.get("tool") == failed_tool and obs.get("status") == "error":
                consecutive += 1
            else:
                break

        if consecutive >= self.retry_limit:
            logger.warning("Tool '%s' failed %d times — switching or giving up", failed_tool, consecutive)
            # If there are other tools available that haven't failed, RETRY (planner will choose differently)
            failed_tools = {o.get("tool") for o in state.observations if o.get("status") == "error"}
            all_tools    = set(state.tool_history)
            untried      = set(self.registry_tools(state)) - failed_tools
            if untried:
                return "RETRY"
            return "FAIL"

        return "RETRY"

    def registry_tools(self, state) -> list:
        """Extract available tool names from tool_history context (no registry access needed)."""
        # We don't have registry here, but RETRY lets the planner pick a different tool
        return []

    def _goal_satisfied(self, state) -> bool:
        last = state.get_last_observation()
        if last["status"] != "success":
            return False

        data = last["data"]
        tool = last.get("tool", "")

        # Search tools never complete a task
        if tool in _SEARCH_TOOLS:
            return False

        if tool == "final_answer":
            return True

        if tool in ("download_paper", "download_file"):
            if isinstance(data, dict) and data.get("status") == "downloaded":
                logger.info("Goal satisfied: %s → %s", tool, data)
                return True
            return False

        if tool == "write_file":
            return isinstance(data, dict) and data.get("status") == "written"

        if tool == "run_python":
            return isinstance(data, dict) and bool(data.get("stdout") or data.get("locals"))

        if tool == "open_application":
            return isinstance(data, dict) and data.get("status") == "success"

        return False

    def _is_looping(self, state) -> bool:
        history = state.tool_history
        if len(history) < self.loop_window:
            return False
        return len(set(history[-self.loop_window:])) == 1

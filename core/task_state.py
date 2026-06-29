from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class TaskState:
    """
    Snapshot of one agentic task execution.
    Now carries a ReasoningResult so all downstream components
    work from reasoned intent rather than raw user input.
    """

    user_request: str

    # Goal
    goal: Optional[str] = None
    success_criteria: List[str] = field(default_factory=list)

    # Reasoning layer output (set after Reasoner runs)
    reasoning: Any = None   # ReasoningResult | None

    # Execution tracking
    steps_taken: int = 0
    tool_history: List[str] = field(default_factory=list)
    observations: List[dict] = field(default_factory=list)

    # Status
    status: str = "RUNNING"

    # Reflection
    reflection_history: List[str] = field(default_factory=list)
    last_decision: Optional[str] = None

    # Memory injection
    conversation_context: str = ""

    # --- Mutators ---

    def set_goal(self, goal: str, success_criteria: List[str]):
        self.goal = goal
        self.success_criteria = success_criteria or []

    def set_reasoning(self, reasoning):
        """Attach the ReasoningResult from the Reasoner layer."""
        self.reasoning = reasoning

    def add_tool_call(self, tool_name: str):
        self.tool_history.append(tool_name)

    def add_observation(self, observation: dict):
        self.observations.append(observation)

    def add_reflection(self, decision: str):
        self.reflection_history.append(decision)
        self.last_decision = decision

    def increment_step(self):
        self.steps_taken += 1

    # --- Queries ---

    def get_last_observation(self) -> Optional[dict]:
        return self.observations[-1] if self.observations else None

    def recent_failures(self, window: int = 3) -> int:
        return sum(
            1 for obs in self.observations[-window:]
            if obs.get("status") == "error"
        )

    def to_dict(self) -> dict:
        return {
            "user_request":    self.user_request,
            "goal":            self.goal,
            "true_intent":     self.reasoning.true_intent if self.reasoning else None,
            "steps_taken":     self.steps_taken,
            "tool_history":    self.tool_history,
            "observations":    self.observations,
            "status":          self.status,
            "last_decision":   self.last_decision,
        }

class ArbiterError(Exception):
    """Base exception for Arbiter."""


class ToolNotFoundError(ArbiterError):
    def __init__(self, tool_name: str):
        super().__init__(f"Tool '{tool_name}' not found in registry.")
        self.tool_name = tool_name


class ToolExecutionError(ArbiterError):
    def __init__(self, tool_name: str, reason: str):
        super().__init__(f"Tool '{tool_name}' failed: {reason}")
        self.tool_name = tool_name
        self.reason = reason


class ValidationError(ArbiterError):
    pass


class LLMError(ArbiterError):
    pass


class ConfigError(ArbiterError):
    pass

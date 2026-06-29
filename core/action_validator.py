from core.logger import get_logger

logger = get_logger("action_validator")

_TYPE_COERCIONS = {
    "string": str,
    "int":    int,
    "float":  float,
    "bool":   bool,
}

# When the LLM uses a wrong param name, map it to the correct one automatically.
# Format: { tool_name: { correct_param: [alias1, alias2, ...] } }
_PARAM_ALIASES = {
    "open_application": {
        "app": ["application", "name", "app_name", "program",
                "executable", "software", "process"],
    },
    "read_file": {
        "path": ["file", "file_path", "filename", "filepath", "location"],
    },
    "write_file": {
        "path":    ["file", "file_path", "filename", "filepath", "location"],
        "content": ["text", "data", "body", "contents", "output"],
    },
    "download_paper": {
        "url": ["link", "pdf_url", "pdf", "href", "source", "paper_url"],
    },
    "download_file": {
        "url":      ["link", "href", "source", "download_url"],
        "filename": ["name", "file", "save_as", "output_name"],
    },
    "search_web": {
        "query": ["search", "term", "q", "search_query", "keywords", "topic"],
    },
    "search_arxiv": {
        "query": ["search", "term", "q", "search_query", "topic",
                  "paper", "title", "keywords"],
    },
    "read_webpage": {
        "url": ["link", "href", "website", "page", "address"],
    },
    "run_python": {
        "code": ["script", "python", "program", "snippet", "source"],
    },
    "list_files": {
        "path": ["directory", "dir", "folder", "location", "where"],
    },
}


class ActionValidator:
    """
    Validates and sanitises planner/reasoner output before execution.

    - Unknown tools → rejected
    - Extra params the tool doesn't declare → stripped (prevents TypeError)
    - Wrong param names → resolved via alias table
    - Type coercion applied where possible
    """

    def __init__(self, registry):
        self.registry = registry

    def validate(self, action: dict) -> tuple:
        if not action or not isinstance(action, dict):
            return False, None, "Action is not a dict."

        tool_name  = action.get("action")
        parameters = action.get("parameters") or {}

        tool = self.registry.get_tool(tool_name)
        if not tool:
            logger.debug("ActionValidator: unknown tool '%s'", tool_name)
            return False, None, f"Unknown tool: '{tool_name}'"

        if tool_name == "final_answer":
            return True, action, None

        expected = getattr(tool, "parameters", {})
        if not isinstance(parameters, dict):
            parameters = {}

        aliases   = _PARAM_ALIASES.get(tool_name, {})
        corrected = {}

        for param_name in expected:
            # 1. Exact match
            if param_name in parameters:
                value = parameters[param_name]
            else:
                # 2. Alias resolution
                value = self._resolve_alias(param_name, aliases, parameters)

            # 3. Type coercion
            type_hint = expected[param_name]
            coerce    = _TYPE_COERCIONS.get(type_hint.split()[0].lower())
            if coerce and value not in ("", None) and not isinstance(value, coerce):
                try:
                    value = coerce(value)
                except (ValueError, TypeError):
                    pass

            corrected[param_name] = value if value is not None else ""

        # Log empty params (tool may fail but at least it will be a clean error)
        empty = [k for k, v in corrected.items() if v == ""]
        if empty:
            logger.debug("ActionValidator: '%s' has empty params: %s", tool_name, empty)

        return True, {"action": tool_name, "parameters": corrected}, None

    @staticmethod
    def _resolve_alias(param_name: str, aliases: dict, parameters: dict):
        for alias in aliases.get(param_name, []):
            if alias in parameters:
                logger.debug("Resolved param '%s' from alias '%s'", param_name, alias)
                return parameters[alias]
        return ""

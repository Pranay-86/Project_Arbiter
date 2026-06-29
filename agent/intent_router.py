from config.config_loader import cfg


class IntentRouter:
    """
    Routes user input to chat mode or task/tool mode.
    """

    _DEFAULT_KEYWORDS = [
        # App control
        "open", "launch", "start", "close", "quit",
        # File operations
        "download", "save", "fetch", "write", "create", "delete",
        "copy", "move", "read", "list", "search", "find", "zip",
        # Execution
        "run", "execute", "install", "compile",
        # Web / info retrieval
        "browse", "go to", "open url", "show me",
        "get me", "give me", "provide", "pull up",
        "look up", "find me", "search for",
        "what is the link", "what's the link", "get the link",
        "youtube", "arxiv", "google",
        # System
        "screenshot", "notify", "type", "click", "press",
        # Media
        "play", "watch", "stream",
    ]

    _CHAT_OVERRIDES = [
        "where did you", "what did you", "did you",
        "have you", "why did", "how did", "when did",
        "what was", "can you explain", "tell me about",
        "i'm asking", "im asking", "what happened",
        "how does", "why is",
    ]

    _QUESTION_STARTERS = (
        "what is ", "what are ", "who is ", "who are ",
        "why does ", "why is ", "how does ", "how is ",
        "when was ", "when is ", "where is ",
    )

    _STRONG_ACTIONS = (
        "download", "open", "run", "create", "write",
        "delete", "launch", "execute", "play", "find",
        "search", "get me", "give me", "provide", "show",
        "youtube", "arxiv", "link",
    )

    def __init__(self):
        self.keywords = cfg.get("agent.tool_keywords", self._DEFAULT_KEYWORDS)

    def requires_tool(self, text: str) -> bool:
        lower = text.lower().strip()

        if len(lower.split()) <= 3:
            return False

        for phrase in self._CHAT_OVERRIDES:
            if lower.startswith(phrase) or f" {phrase}" in lower:
                return False

        if any(lower.startswith(q) for q in self._QUESTION_STARTERS):
            if not any(a in lower for a in self._STRONG_ACTIONS):
                return False

        return any(kw in lower for kw in self.keywords)

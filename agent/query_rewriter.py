from agent.prompts import SYSTEM_PROMPT_TOOLS
from core.logger import get_logger

logger = get_logger("query_rewriter")

# Tools that benefit from query rewriting
_REWRITE_TARGETS = {"search_web", "search_arxiv"}


class QueryRewriter:
    """
    Rewrites user queries to be optimized for specific search tools.

    Previously broken: imported non-existent SYSTEM_PROMPT and called
    self.llm.generate() which also didn't exist.
    Now accepts llm via constructor and uses llm.chat().
    """

    def __init__(self, llm):
        self.llm = llm

    def rewrite(self, query: str, tool: str) -> str:
        if tool not in _REWRITE_TARGETS:
            return query

        instructions = {
            "search_web":   "Optimize for a general internet search engine. Be concise and specific.",
            "search_arxiv": "Optimize for academic paper search on arXiv. Use technical terms and field names.",
        }

        prompt = (
            f"{SYSTEM_PROMPT_TOOLS}\n\n"
            "You are improving a search query for better results.\n\n"
            f"Original query: {query}\n"
            f"Target tool: {tool}\n"
            f"Instruction: {instructions[tool]}\n\n"
            "Return ONLY the rewritten query. No explanation."
        )

        result = self.llm.chat(prompt).strip()
        logger.debug("QueryRewriter: '%s' → '%s' (tool=%s)", query, result, tool)
        return result or query

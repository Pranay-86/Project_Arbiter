from models.llm_router import LLMRouter
from agent.prompts import SYSTEM_PROMPT_CHAT


class ResponseGenerator:
    """
    Synthesizes a natural-language answer from tool results.
    Previously broken: called self.llm.generate() which didn't exist.
    Now correctly uses self.llm.chat().
    """

    def __init__(self, llm: LLMRouter):
        self.llm = llm

    def generate(self, query: str, tool_results) -> str:
        identity = self.llm.identity

        prompt = (
            f"{SYSTEM_PROMPT_CHAT}\n\n"
            f"The user asked:\n{query}\n\n"
            f"Retrieved information:\n{tool_results}\n\n"
            f"Generate a clear and helpful answer as {identity}. "
            "Do not list raw links unless necessary. Explain the answer naturally."
        )

        return self.llm.chat(prompt)

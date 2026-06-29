from memory.vector_store import VectorStore
from config.config_loader import cfg
from core.logger import get_logger

logger = get_logger("conversation_memory")


class ConversationMemory:
    """
    Stores and retrieves conversation turns using semantic vector search.
    Each turn is stored as "User: ...\nArbiter: ..." for natural retrieval.
    """

    def __init__(self):
        self.store    = VectorStore()
        self._identity = cfg.get("models.identity_name", "Arbiter")

    def add(self, user: str, assistant: str):
        text = f"User: {user}\n{self._identity}: {assistant}"
        self.store.add(text=text, metadata={"type": "conversation"})

    def retrieve(self, query: str, k: int | None = None) -> list[str]:
        k = k or cfg.get("memory.retrieval_k", 5)
        return self.store.search(query, k=k)

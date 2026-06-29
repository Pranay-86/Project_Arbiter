import chromadb
from sentence_transformers import SentenceTransformer
from config.config_loader import cfg
from core.logger import get_logger

logger = get_logger("vector_store")


class VectorStore:
    """
    Persistent semantic vector store backed by ChromaDB + SentenceTransformers.
    All configuration (path, collection, model) is read from settings.yaml.
    """

    def __init__(self):
        persist_path     = cfg.get("memory.persist_path",     "memory_db")
        collection_name  = cfg.get("memory.collection_name",  "arbiter_knowledge")
        embedding_model  = cfg.get("memory.embedding_model",  "all-MiniLM-L6-v2")

        self.client = chromadb.PersistentClient(path=persist_path)
        self.collection = self.client.get_or_create_collection(name=collection_name)
        self.model = SentenceTransformer(embedding_model)
        logger.info("VectorStore ready: collection=%s model=%s", collection_name, embedding_model)

    def add(self, text: str, metadata: dict | None = None):
        embedding = self.model.encode(text).tolist()
        doc_id    = str(abs(hash(text)))
        self.collection.upsert(
            documents=[text],
            embeddings=[embedding],
            metadatas=[metadata or {}],
            ids=[doc_id],
        )

    def search(self, query: str, k: int | None = None) -> list[str]:
        if k is None:
            k = cfg.get("memory.retrieval_k", 5)
        embedding = self.model.encode(query).tolist()
        results   = self.collection.query(query_embeddings=[embedding], n_results=k)
        return results.get("documents", [[]])[0]

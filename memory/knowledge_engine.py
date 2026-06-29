from memory.knowledge_graph import KnowledgeGraph
from memory.knowledge_extractor import KnowledgeExtractor
from config.config_loader import cfg
from core.logger import get_logger

logger = get_logger("knowledge_engine")


class KnowledgeEngine:
    """
    Hybrid retrieval engine combining semantic vector search with a
    concept-level knowledge graph.
    """

    def __init__(self, llm, vector_store):
        self.llm   = llm
        self.store = vector_store
        self.graph = KnowledgeGraph()
        self.extractor = KnowledgeExtractor(llm)

    # ------------------------------------------------------------------ #
    #  Ingestion                                                           #
    # ------------------------------------------------------------------ #

    def ingest(self, content: str, source: str):
        chunks = self._chunk(content)
        for chunk in chunks:
            summary = self._summarize(chunk)
            self.store.add(text=summary, metadata={"source": source})

            structured = self.extractor.extract(chunk)
            for concept in structured["concepts"]:
                self.graph.add_node(concept)
            for rel in structured["relations"]:
                self.graph.add_edge(rel["source"], rel["relation"], rel["target"])

        logger.info("Ingested %d chunks from %s", len(chunks), source)

    # ------------------------------------------------------------------ #
    #  Retrieval                                                           #
    # ------------------------------------------------------------------ #

    def retrieve(self, query: str) -> dict:
        k        = cfg.get("memory.retrieval_k", 5)
        semantic = self.store.search(query, k=k)

        graph_data = []
        for doc in semantic:
            graph_data.extend(self.graph.get_related(doc))

        return {"semantic": semantic, "graph": graph_data}

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _chunk(self, text: str) -> list[str]:
        size = cfg.get("memory.chunk_size", 500)
        return [text[i:i + size] for i in range(0, len(text), size)]

    def _summarize(self, text: str) -> str:
        return self.llm.chat(f"Summarize concisely:\n{text[:1000]}")

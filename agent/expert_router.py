from core.logger import get_logger

logger = get_logger("curiosity_engine")


class CuriosityEngine:
    """
    Proactively ingests web content into the knowledge engine during idle time.
    Triggered by the Scheduler when CPU is idle.
    """

    def __init__(self, llm, knowledge_engine, tool_executor):
        self.llm = llm
        self.knowledge = knowledge_engine
        self.executor = tool_executor

    def run(self, sources: list):
        for source in sources:
            result = self.executor.execute("read_webpage", {"url": source})

            if result["status"] != "success":
                logger.warning("CuriosityEngine: failed to fetch %s — %s",
                               source, result.get("error"))
                continue

            content = result["data"]
            self.knowledge.ingest(content, source)
            logger.info("CuriosityEngine: ingested %s", source)

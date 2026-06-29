import json
from agent.prompts import SYSTEM_PROMPT_TOOLS
from core.logger import get_logger

logger = get_logger("knowledge_extractor")


class KnowledgeExtractor:
    """
    Uses the LLM to extract structured concepts and relations from raw text.
    """

    def __init__(self, llm):
        self.llm = llm

    def extract(self, text: str) -> dict:
        prompt = (
            f"{SYSTEM_PROMPT_TOOLS}\n\n"
            "Extract structured knowledge from the text below.\n\n"
            "Return JSON ONLY:\n"
            '{\n'
            '  "concepts": ["concept1", "concept2"],\n'
            '  "relations": [\n'
            '    {"source": "...", "relation": "...", "target": "..."}\n'
            '  ]\n'
            '}\n\n'
            f"Text:\n{text[:1500]}"
        )

        response = self.llm.chat(prompt)

        try:
            clean = response.strip().strip("```json").strip("```").strip()
            data  = json.loads(clean)
            return {
                "concepts":  data.get("concepts", []),
                "relations": data.get("relations", []),
            }
        except Exception:
            logger.warning("KnowledgeExtractor: parse failed.")
            return {"concepts": [], "relations": []}

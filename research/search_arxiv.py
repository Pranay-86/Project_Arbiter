import requests
import xml.etree.ElementTree as ET
from tools.tool_base import Tool
from config.config_loader import cfg
from core.logger import get_logger

logger = get_logger("search_arxiv")

_ARXIV_API = "https://export.arxiv.org/api/query"
_NS = {"atom": "http://www.w3.org/2005/Atom"}


class SearchArxivTool(Tool):

    name = "search_arxiv"
    description = "Search for academic papers on arXiv by keyword or topic."
    parameters = {
        "query": "string — search terms or paper topic"
    }

    def execute(self, query: str) -> list:
        max_results = cfg.get("search.max_results", 5)
        timeout     = cfg.get("agent.timeout", 30)

        try:
            response = requests.get(
                _ARXIV_API,
                params={"search_query": query, "start": 0, "max_results": max_results},
                timeout=timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.error("search_arxiv failed: %s", exc)
            return {"error": str(exc)}

        root = ET.fromstring(response.text)
        papers = []

        for entry in root.findall("atom:entry", _NS):
            title   = (entry.find("atom:title",   _NS).text or "").strip()
            summary = (entry.find("atom:summary", _NS).text or "").strip()
            pdf_url = next(
                (lnk.attrib["href"] for lnk in entry.findall("atom:link", _NS)
                 if lnk.attrib.get("title") == "pdf"),
                ""
            )
            papers.append({"title": title, "summary": summary, "pdf": pdf_url})

        return papers

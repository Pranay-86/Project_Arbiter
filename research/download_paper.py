import requests
from pathlib import Path
from tools.tool_base import Tool
from config.config_loader import cfg
from core.logger import get_logger

logger = get_logger("download_paper")


class DownloadPaperTool(Tool):

    name = "download_paper"
    description = "Download a research paper PDF from a given URL (e.g. from arXiv)."
    parameters = {
        "url": "string — direct PDF URL of the paper"
    }

    def execute(self, url: str) -> dict:
        papers_dir = cfg.get("tools.papers_dir", "papers")
        timeout    = cfg.get("agent.timeout", 30)

        Path(papers_dir).mkdir(parents=True, exist_ok=True)

        filename = url.rstrip("/").split("/")[-1]
        if not filename.endswith(".pdf"):
            filename += ".pdf"

        save_path = Path(papers_dir) / filename

        try:
            response = requests.get(url, timeout=timeout, stream=True)
            response.raise_for_status()
            with save_path.open("wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        except requests.RequestException as exc:
            logger.error("download_paper failed: %s", exc)
            return {"error": str(exc)}

        logger.info("Paper saved: %s", save_path)
        return {"status": "downloaded", "path": str(save_path)}

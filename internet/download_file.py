import os
import requests
from pathlib import Path
from tools.tool_base import Tool
from config.config_loader import cfg
from core.logger import get_logger

logger = get_logger("download_file")


class DownloadFileTool(Tool):

    name = "download_file"
    description = "Download a file from a URL and save it locally."
    parameters = {
        "url":      "string — direct URL of the file to download",
        "filename": "string — optional filename to save as (auto-detected if omitted)"
    }

    def execute(self, url: str, filename: str = "") -> dict:
        timeout  = cfg.get("agent.timeout", 30)
        save_dir = cfg.get("tools.download_dir", "downloads")

        Path(save_dir).mkdir(parents=True, exist_ok=True)

        if not filename:
            filename = url.split("/")[-1].split("?")[0] or "downloaded_file"

        save_path = Path(save_dir) / filename

        try:
            response = requests.get(url, timeout=timeout, stream=True)
            response.raise_for_status()
            with save_path.open("wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        except requests.RequestException as exc:
            logger.error("download_file failed: %s", exc)
            return {"error": str(exc)}

        logger.info("Downloaded %s → %s", url, save_path)
        return {"status": "downloaded", "file": str(save_path)}

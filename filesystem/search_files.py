import os
from pathlib import Path
from tools.tool_base import Tool
from config.config_loader import cfg
from core.logger import get_logger

logger = get_logger("search_files")


class SearchFilesTool(Tool):

    name = "search_files"
    description = (
        "Search for files by name pattern or text content within a folder. "
        "Use to find where a file is, or find files containing specific text."
    )
    parameters = {
        "folder":  "string — folder to search in (e.g. C:/Users/me/Documents)",
        "name":    "string — filename pattern to match (e.g. *.py, report*.docx)",
        "content": "string — optional text to search for inside files"
    }

    def execute(self, folder: str, name: str = "", content: str = "") -> dict:
        base = Path(folder).expanduser()
        if not base.exists():
            return {"error": f"Folder not found: '{folder}'"}

        max_results = cfg.get("tools.search_max_results", 50)
        pattern     = name.strip() or "*"
        matches     = []

        try:
            for p in base.rglob(pattern):
                if len(matches) >= max_results:
                    break
                if not p.is_file():
                    continue

                if content:
                    try:
                        text = p.read_text(encoding="utf-8", errors="ignore")
                        if content.lower() not in text.lower():
                            continue
                    except Exception:
                        continue

                matches.append(str(p))

        except PermissionError as exc:
            return {"error": f"Permission denied: {exc}"}

        logger.info("search_files: %d matches in %s", len(matches), base)
        return {"matches": matches, "count": len(matches), "folder": str(base)}

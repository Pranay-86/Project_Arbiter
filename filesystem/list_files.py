import os
from pathlib import Path
from tools.tool_base import Tool
from config.config_loader import cfg
from core.logger import get_logger

logger = get_logger("list_files")


class ListFilesTool(Tool):

    name = "list_files"
    description = (
        "List files and folders inside a directory. "
        "Accepts an absolute path or a folder name to search for."
    )
    parameters = {
        "path": "string — directory path or folder name"
    }

    def _search_roots(self) -> list[Path]:
        raw = cfg.get("tools.search_roots", ["~", "~/Desktop", "~/Documents", "~/Downloads"])
        return [Path(r).expanduser() for r in raw]

    def resolve_path(self, path: str) -> Path | None:
        p = Path(path).expanduser()
        if p.exists():
            return p
        for root in self._search_roots():
            candidate = root / path
            if candidate.exists():
                return candidate
        return None

    def execute(self, path: str):
        resolved = self.resolve_path(path)
        if resolved is None:
            return {"error": f"Could not locate directory: '{path}'"}
        if not resolved.is_dir():
            return {"error": f"Path is not a directory: '{resolved}'"}
        try:
            return sorted(os.listdir(resolved))
        except PermissionError:
            return {"error": f"Permission denied: '{resolved}'"}

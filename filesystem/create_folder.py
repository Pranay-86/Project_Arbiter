from pathlib import Path
from tools.tool_base import Tool
from core.logger import get_logger

logger = get_logger("create_folder")


class CreateFolderTool(Tool):

    name = "create_folder"
    description = "Create a new folder (and any missing parent folders)."
    parameters = {
        "path": "string — full path of the folder to create"
    }

    def execute(self, path: str) -> dict:
        p = Path(path).expanduser()
        try:
            p.mkdir(parents=True, exist_ok=True)
            logger.info("create_folder: %s", p)
            return {"status": "created", "path": str(p)}
        except Exception as exc:
            return {"error": str(exc)}

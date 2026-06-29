import shutil
from pathlib import Path
from tools.tool_base import Tool
from core.logger import get_logger

logger = get_logger("move_file")


class MoveFileTool(Tool):

    name = "move_file"
    description = "Move or rename a file or folder."
    parameters = {
        "source":      "string — current path of the file or folder",
        "destination": "string — new path or destination folder"
    }

    def execute(self, source: str, destination: str) -> dict:
        src  = Path(source).expanduser().resolve()
        dest = Path(destination).expanduser()

        if not src.exists():
            return {"error": f"Source not found: '{source}'"}

        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest))
            logger.info("move_file: %s → %s", src, dest)
            return {"status": "moved", "source": str(src), "destination": str(dest)}
        except Exception as exc:
            return {"error": str(exc)}

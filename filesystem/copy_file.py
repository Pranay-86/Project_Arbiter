import shutil
from pathlib import Path
from tools.tool_base import Tool
from core.logger import get_logger

logger = get_logger("copy_file")


class CopyFileTool(Tool):

    name = "copy_file"
    description = "Copy a file or folder from one location to another."
    parameters = {
        "source":      "string — path to the file or folder to copy",
        "destination": "string — destination path"
    }

    def execute(self, source: str, destination: str) -> dict:
        src  = Path(source).expanduser().resolve()
        dest = Path(destination).expanduser()

        if not src.exists():
            return {"error": f"Source not found: '{source}'"}

        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                shutil.copytree(str(src), str(dest), dirs_exist_ok=True)
            else:
                shutil.copy2(str(src), str(dest))
            logger.info("copy_file: %s → %s", src, dest)
            return {"status": "copied", "source": str(src), "destination": str(dest)}
        except Exception as exc:
            return {"error": str(exc)}

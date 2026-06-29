import shutil
from pathlib import Path
from tools.tool_base import Tool
from core.logger import get_logger

logger = get_logger("delete_file")

# Paths that are never allowed to be deleted regardless of what is asked
_PROTECTED = {"/", "C:\\", "C:/", "/home", "/etc", "/usr", "/bin",
              "/system32", "C:\\Windows"}


class DeleteFileTool(Tool):

    name = "delete_file"
    description = (
        "Delete a file or folder. "
        "Protected system paths are blocked. "
        "Use with care — deletion is permanent."
    )
    parameters = {
        "path": "string — path to the file or folder to delete"
    }

    def execute(self, path: str) -> dict:
        p = Path(path).expanduser().resolve()

        # Safety: block protected paths
        if str(p) in _PROTECTED or any(str(p).startswith(pp) for pp in _PROTECTED):
            return {"error": f"Refusing to delete protected path: '{p}'"}

        if not p.exists():
            return {"error": f"Path not found: '{path}'"}

        try:
            if p.is_dir():
                shutil.rmtree(str(p))
                logger.info("delete_file: removed directory %s", p)
            else:
                p.unlink()
                logger.info("delete_file: deleted %s", p)
            return {"status": "deleted", "path": str(p)}
        except Exception as exc:
            return {"error": str(exc)}

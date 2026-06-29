from pathlib import Path
from tools.tool_base import Tool
from core.logger import get_logger

logger = get_logger("write_file")


class WriteFileTool(Tool):

    name = "write_file"
    description = (
        "Write text content to a local file. "
        "Creates parent directories if they do not exist."
    )
    parameters = {
        "path":    "string — full path to the file",
        "content": "string — text content to write"
    }

    def execute(self, path: str, content: str) -> dict:
        p = Path(path).expanduser()
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            logger.info("write_file: wrote %d bytes to %s", len(content), p)
            return {"status": "written", "path": str(p), "bytes": len(content)}
        except PermissionError:
            return {"error": f"Permission denied writing to '{p}'"}
        except Exception as exc:
            return {"error": str(exc)}

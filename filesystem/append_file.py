from pathlib import Path
from tools.tool_base import Tool
from core.logger import get_logger

logger = get_logger("append_file")


class AppendFileTool(Tool):

    name = "append_file"
    description = "Append text to the end of an existing file without overwriting it."
    parameters = {
        "path":    "string — full path to the file",
        "content": "string — text to append"
    }

    def execute(self, path: str, content: str) -> dict:
        p = Path(path).expanduser()
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            with p.open("a", encoding="utf-8") as f:
                f.write(content)
            logger.info("append_file: %d bytes → %s", len(content), p)
            return {"status": "appended", "path": str(p), "bytes_added": len(content)}
        except Exception as exc:
            return {"error": str(exc)}

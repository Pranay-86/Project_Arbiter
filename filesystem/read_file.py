from pathlib import Path
from tools.tool_base import Tool
from core.logger import get_logger

logger = get_logger("read_file")


class ReadFileTool(Tool):

    name = "read_file"
    description = (
        "Read the contents of a local file. "
        "Provide an absolute path or a relative path."
    )
    parameters = {
        "path": "string — full path to the file"
    }

    def execute(self, path: str) -> str:
        p = Path(path).expanduser()

        if not p.exists():
            return {"error": f"File not found: '{path}'"}
        if not p.is_file():
            return {"error": f"Path is not a file: '{path}'"}

        for encoding in ("utf-8", "latin-1", "cp1252"):
            try:
                return p.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue

        return {"error": f"Could not decode file '{path}' with any supported encoding."}

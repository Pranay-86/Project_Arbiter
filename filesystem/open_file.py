import os
import platform
import subprocess
from pathlib import Path
from tools.tool_base import Tool
from core.logger import get_logger

logger = get_logger("open_file")
_OS = platform.system()


class OpenFileTool(Tool):

    name = "open_file"
    description = (
        "Open any file with its default application — same as double-clicking it. "
        "Works for videos, PDFs, images, documents, code files, text files, etc."
    )
    parameters = {
        "path": "string — full or relative path to the file to open"
    }

    def execute(self, path: str) -> dict:
        if not path or not path.strip():
            return {"error": "No file path provided."}

        p = Path(path).expanduser().resolve()
        if not p.exists():
            return {"error": f"File not found: '{path}'"}

        try:
            if _OS == "Windows":
                self._open_windows(str(p))
            elif _OS == "Darwin":
                subprocess.Popen(
                    ["open", str(p)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                )
            else:
                subprocess.Popen(
                    ["xdg-open", str(p)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                )

            logger.info("open_file: '%s'", p)
            return {"status": "opened", "path": str(p)}

        except Exception as exc:
            logger.error("open_file error: %s", exc)
            return {"error": str(exc)}

    @staticmethod
    def _open_windows(path: str):
        """
        On Windows, os.startfile() inherits the parent's console handles,
        which is why VS Code (and other apps) print their startup logs to
        our terminal.

        Fix: use PowerShell Start-Process with:
          -WindowStyle Hidden  → suppresses the child's console window
          -PassThru            → returns immediately without waiting

        This fully detaches the child from our terminal's stdout/stderr.
        """
        escaped = path.replace("'", "''")   # escape single quotes for PS
        ps_cmd  = f"Start-Process '{escaped}'"

        subprocess.Popen(
            [
                "powershell", "-NoProfile", "-NonInteractive",
                "-WindowStyle", "Hidden",
                "-ExecutionPolicy", "Bypass",
                "-Command", ps_cmd,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            # creationflags detaches the new process from our console on Windows
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        )

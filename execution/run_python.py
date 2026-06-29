import io
import sys
import signal
from tools.tool_base import Tool
from config.config_loader import cfg
from core.logger import get_logger

logger = get_logger("run_python")


def _timeout_handler(signum, frame):
    raise TimeoutError("Python execution timed out.")


class RunPythonTool(Tool):

    name = "run_python"
    description = (
        "Execute a Python code snippet and return its stdout output and "
        "any local variables it defines. Use for calculations and data processing."
    )
    parameters = {
        "code": "string — valid Python code to execute"
    }

    def execute(self, code: str) -> dict:
        timeout = cfg.get("tools.run_python_timeout", 10)

        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()

        local_vars: dict = {}

        try:
            # SIGALRM is Unix-only; skip on Windows
            use_alarm = hasattr(signal, "SIGALRM")
            if use_alarm:
                signal.signal(signal.SIGALRM, _timeout_handler)
                signal.alarm(timeout)

            exec(code, {"__builtins__": __builtins__}, local_vars)  # noqa: S102

            if use_alarm:
                signal.alarm(0)  # cancel alarm

        except TimeoutError:
            return {"error": f"Execution exceeded {timeout}s timeout."}
        except Exception as exc:
            return {"error": f"{type(exc).__name__}: {exc}"}
        finally:
            sys.stdout = old_stdout

        stdout_output = buffer.getvalue()

        # Filter out non-serialisable objects from local_vars
        safe_vars = {
            k: v for k, v in local_vars.items()
            if not k.startswith("_") and isinstance(v, (str, int, float, bool, list, dict, type(None)))
        }

        return {"stdout": stdout_output, "locals": safe_vars}

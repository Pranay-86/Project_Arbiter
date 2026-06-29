import sys
import os
import platform
from config.config_loader import cfg
from core.logger import get_logger

logger = get_logger("cli_interface")
_OS = platform.system()


class CLIInterface:
    """
    Interactive CLI loop for Arbiter.

    On Windows, child processes launched by tools can inherit the console's
    stdout handle and print their startup logs directly to our terminal even
    after we redirect to DEVNULL — because Windows console handles are
    inherited by default at the OS level, not just at the Python level.

    We work around this by:
    1. Using sys.stdout.write + flush for all output (not print)
    2. Printing a clear separator after each task result so the user can
       always see where Arbiter's output ends and any leaked logs begin
    """

    def __init__(self, agent):
        self.agent      = agent
        self.debug_mode = cfg.get("system.debug_mode", False)
        self._identity  = cfg.get("models.identity_name", "Arbiter")

    def _write(self, text: str):
        sys.stdout.write(text + "\n")
        sys.stdout.flush()

    def _prompt(self) -> str:
        sys.stdout.write(f"\n{self._identity} > ")
        sys.stdout.flush()
        try:
            line = sys.stdin.readline()
            return line.strip()
        except (EOFError, KeyboardInterrupt):
            return "exit"

    def start(self):
        self._write(
            f"{self._identity} CLI started. "
            "Type 'exit' to quit, 'debug on/off' to toggle debug."
        )

        while True:
            user_input = self._prompt()

            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit"):
                self._write("Goodbye.")
                break

            if user_input.lower() in ("debug on", "debug mode on"):
                self.debug_mode = True
                self._write("Debug mode enabled.")
                continue

            if user_input.lower() in ("debug off", "debug mode off"):
                self.debug_mode = False
                self._write("Debug mode disabled.")
                continue

            result = self.agent.run(user_input)

            if self.debug_mode:
                logger.debug("Input: %s | Output: %s", user_input, result)

            # Flush stdout before printing result to push past any leaked child output
            sys.stdout.flush()
            self._write(str(result))
            # Print a blank line as a visual separator so the user can clearly
            # see where Arbiter's response ends, even if child logs follow
            sys.stdout.flush()

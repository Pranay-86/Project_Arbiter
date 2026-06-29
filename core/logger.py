import logging
import os
from config.config_loader import cfg


def _setup_logger() -> logging.Logger:
    log_dir = cfg.get("logging.log_dir", "logs")
    log_file = cfg.get("logging.log_file", "arbiter.log")
    level_str = cfg.get("logging.level", "INFO")
    level = getattr(logging, level_str.upper(), logging.INFO)

    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_file)

    logging.basicConfig(
        filename=log_path,
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s - %(message)s",
    )
    return logging.getLogger("arbiter")


_root_logger = _setup_logger()


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_step(logger: logging.Logger, step: int, tool: str, params: dict, result):
    logger.info("STEP %d | TOOL: %s | PARAMS: %s | RESULT: %s",
                step, tool, params, result)

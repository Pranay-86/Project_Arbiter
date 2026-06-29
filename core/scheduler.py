import time
import psutil
from config.config_loader import cfg
from core.logger import get_logger

logger = get_logger("scheduler")


class Scheduler:
    """
    Runs the CuriosityEngine when the system is idle.
    Idle threshold and CPU percentage are read from settings.yaml.
    """

    def __init__(self, curiosity_engine):
        self.engine          = curiosity_engine
        self.idle_interval   = cfg.get("system.idle_threshold",    60)
        self.cpu_threshold   = cfg.get("system.idle_cpu_threshold", 10)

    def is_idle(self) -> bool:
        return psutil.cpu_percent(interval=1) < self.cpu_threshold

    def run(self, sources: list):
        logger.info("Scheduler started. Interval=%ds CPU_threshold=%d%%",
                    self.idle_interval, self.cpu_threshold)
        while True:
            time.sleep(self.idle_interval)
            if self.is_idle():
                logger.info("System idle — running CuriosityEngine.")
                self.engine.run(sources)

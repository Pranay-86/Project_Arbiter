import os
import yaml
from pathlib import Path


class ConfigLoader:
    """
    Singleton YAML config loader with dot-notation access and
    environment-variable override support.

    ENV override convention:  ARBITER__MODELS__DEFAULT_MODEL=xyz
    (double-underscore as separator, all uppercase)
    """

    _instance = None

    def __new__(cls, config_path: str = "config/settings.yaml"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def __init__(self, config_path: str = "config/settings.yaml"):
        if self._loaded:
            return
        self.config_path = Path(config_path)
        self.config = self._load()
        self._apply_env_overrides()
        self._loaded = True

    # ------------------------------------------------------------------ #

    def _load(self) -> dict:
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Config not found: {self.config_path}. "
                "Expected at config/settings.yaml"
            )
        with self.config_path.open("r") as f:
            return yaml.safe_load(f) or {}

    def _apply_env_overrides(self):
        """
        Allow any setting to be overridden via environment variable.
        Example: ARBITER__MODELS__DEFAULT_MODEL=mistral:7b
        """
        prefix = "ARBITER__"
        for key, value in os.environ.items():
            if key.startswith(prefix):
                parts = key[len(prefix):].lower().split("__")
                node = self.config
                for part in parts[:-1]:
                    node = node.setdefault(part, {})
                node[parts[-1]] = self._coerce(value)

    @staticmethod
    def _coerce(value: str):
        """Try to coerce env strings to int/float/bool."""
        if value.lower() in ("true", "1", "yes"):
            return True
        if value.lower() in ("false", "0", "no"):
            return False
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
        return value

    # ------------------------------------------------------------------ #

    def get(self, key_path: str, default=None):
        """
        Dot-notation access.  e.g.  cfg.get("models.default_model")
        """
        keys = key_path.split(".")
        value = self.config
        for key in keys:
            if not isinstance(value, dict) or key not in value:
                return default
            value = value[key]
        return value

    def reload(self):
        """Force reload from disk (useful during testing)."""
        self._loaded = False
        self.__init__(str(self.config_path))


# Module-level convenience singleton
cfg = ConfigLoader()

import logging
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)


class ConfigHandler:
    """Loads YAML configs from config/standard/ and config/configurable/."""

    def __init__(self, config_dir: str = "./config"):
        self.config_dir = Path(config_dir)

    def load_main_config(self) -> dict:
        return self._load(self.config_dir / "main_config.yaml")

    def load_standard_config(self, indicator: str) -> dict:
        path = self.config_dir / "standard" / f"{indicator.lower()}.yaml"
        if not path.exists():
            logger.warning(f"No standard config for {indicator}, using empty dict")
            return {}
        return self._load(path)

    def load_configurable_config(self, indicator: str) -> dict:
        path = self.config_dir / "configurable" / f"{indicator.lower()}.yaml"
        if not path.exists():
            return {}
        return self._load(path)

    @staticmethod
    def _load(path: Path) -> dict:
        with open(path, "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}

import atexit
import logging
import tomllib
from importlib.resources import files
from logging.config import dictConfig
from logging.handlers import QueueListener
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from logging import Handler
    from queue import Queue
    from typing import Any

    from pipe_ping.tools.settings import PipePingSettings


def logging_config(
    settings: "PipePingSettings", console_level: int
) -> "dict[str, Any]":
    """Load ``logging.toml`` and fill in the values known only at runtime."""
    config_text = files("pipe_ping.tools").joinpath("logging.toml").read_text()
    config = tomllib.loads(config_text)

    handlers = config["handlers"]
    handlers["console"]["level"] = console_level
    handlers["structured"]["filename"] = settings.structured_logging.path
    handlers["structured"]["maxBytes"] = settings.structured_logging.max_bytes
    handlers["structured"]["backupCount"] = settings.structured_logging.backup_count

    return config


class AutoStartQueueListener(QueueListener):
    def __init__(
        self, queue: "Queue", *handlers: "Handler", respect_handler_level: bool = False
    ) -> None:
        super().__init__(queue, *handlers, respect_handler_level=respect_handler_level)
        self.start()
        atexit.register(self.stop)


def initialize_logging(
    settings: "PipePingSettings", console_level: int = logging.WARNING
) -> None:
    Path(settings.structured_logging.path).parent.mkdir(parents=True, exist_ok=True)

    dictConfig(logging_config(settings, console_level))

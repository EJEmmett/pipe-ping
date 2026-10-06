from typing import TYPE_CHECKING, Protocol

from pipe_ping.plugin.discovery import Plugin

if TYPE_CHECKING:
    from pipe_ping.models.provider import PipelineResult


NOTIFIER_GROUP = "pipe-ping.notifiers"


class NotifierPlugin(Plugin, Protocol):
    async def notify(self, results: "list[PipelineResult]") -> None: ...

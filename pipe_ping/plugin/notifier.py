from typing import TYPE_CHECKING, Protocol

from pipe_ping.plugin.discovery import Plugin

if TYPE_CHECKING:
    from pipe_ping.models.provider import PipelineResult


NOTIFIER_GROUP = "pipe-ping.notifiers"


class NotifierPlugin(Plugin, Protocol):
    """Reports pipeline run changes to the user.

    Register notifiers in the ``pipe-ping.notifiers`` entry point group.
    """

    async def notify(self, results: "list[PipelineResult]") -> None:
        """Report *results*, the pipeline runs returned by the repository."""
        ...

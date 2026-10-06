from typing import TYPE_CHECKING, Protocol

from pipe_ping.plugin.discovery import Plugin

if TYPE_CHECKING:
    from pipe_ping.models.provider import PipelineResult


PROVIDER_GROUP = "pipe-ping.providers"


class ProviderPlugin(Plugin, Protocol):
    """Fetches pipeline runs from a CI/CD service.

    Register providers in the ``pipe-ping.providers`` entry point group.
    """

    async def poll(self) -> "list[PipelineResult]":
        """Return the current state of recent pipeline runs."""
        ...

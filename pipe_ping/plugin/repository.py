from typing import TYPE_CHECKING, Protocol

from pipe_ping.plugin.discovery import Plugin

if TYPE_CHECKING:
    from pipe_ping.models.provider import PipelineResult


REPOSITORY_GROUP = "pipe-ping.repository"


class RepositoryPlugin(Plugin, Protocol):
    async def save(self, results: "list[PipelineResult]") -> "list[PipelineResult]":
        """Persist *results* and return the ones notifiers should hear about."""
        ...

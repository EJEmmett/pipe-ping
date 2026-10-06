from typing import TYPE_CHECKING, Protocol

from pipe_ping.plugin.discovery import Plugin

if TYPE_CHECKING:
    from pipe_ping.models.provider import PipelineResult


REPOSITORY_GROUP = "pipe-ping.repository"


class RepositoryPlugin(Plugin, Protocol):
    """Stores pipeline runs and decides which changes to report.

    Register a repository in the ``pipe-ping.repository`` entry point group.
    """

    async def save(self, results: "list[PipelineResult]") -> "list[PipelineResult]":
        """Store *results* and return the ones to notify about."""
        ...

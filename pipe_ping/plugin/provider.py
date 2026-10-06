from typing import TYPE_CHECKING, Protocol

from pipe_ping.plugin.discovery import Plugin

if TYPE_CHECKING:
    from pipe_ping.models.provider import PipelineResult


PROVIDER_GROUP = "pipe-ping.providers"


class ProviderPlugin(Plugin, Protocol):
    async def poll(self) -> "list[PipelineResult]": ...

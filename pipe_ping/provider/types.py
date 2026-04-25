from collections.abc import Awaitable, Callable

from aiohttp import ClientSession

from pipe_ping.models.provider import PipelineResult

type AwaitableProvider = Callable[[ClientSession], Awaitable[list[PipelineResult]]]

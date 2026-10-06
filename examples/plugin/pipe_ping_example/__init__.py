from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipe_ping.models.provider import PipelineResult


class ExampleProvider:
    async def setup(self) -> None: ...

    async def teardown(self) -> None: ...

    async def poll(self) -> "list[PipelineResult]":
        return []


class ExampleNotifier:
    async def setup(self) -> None: ...

    async def teardown(self) -> None: ...

    async def notify(self, results: "list[PipelineResult]") -> None:
        for result in results:
            print(f"{result.repo} {result.branch}: {result.status.value}")

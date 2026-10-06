from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipe_ping.models.provider import PipelineResult


class MemoryRepository:
    """Store the latest result for each pipeline run in memory.

    Results are keyed by ``(provider, id)``. Stored results are lost when
    Pipe-Ping exits.
    """

    results: "dict[tuple[str, str], PipelineResult]"
    primed_providers: set[str]

    def __init__(self) -> None:
        self.results = {}
        self.primed_providers = set()

    async def setup(self) -> None: ...
    async def teardown(self) -> None: ...

    async def save(self, results: "list[PipelineResult]") -> "list[PipelineResult]":
        """Store *results* and return pipeline runs that are new or changed status.

        The first save for each provider records its pipeline runs and returns
        nothing, so existing pipeline runs are not reported at startup.
        """
        changed: list[PipelineResult] = []

        for result in results:
            key = (result.provider, result.id)
            previous = self.results.get(key)
            self.results[key] = result

            if result.provider not in self.primed_providers:
                continue

            if previous is None or previous.status != result.status:
                changed.append(result)

        self.primed_providers.update(result.provider for result in results)

        return changed

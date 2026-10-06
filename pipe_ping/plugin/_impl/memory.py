from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipe_ping.models.provider import PipelineResult


class MemoryRepository:
    """Keeps the latest result per pipeline run in memory and reports transitions.

    Results are keyed by ``(provider, id)`` so run ids from different providers
    cannot collide. State is lost on restart.
    """

    results: "dict[tuple[str, str], PipelineResult]"
    primed_providers: set[str]

    def __init__(self) -> None:
        self.results = {}
        self.primed_providers = set()

    async def setup(self) -> None: ...
    async def teardown(self) -> None: ...

    async def save(self, results: "list[PipelineResult]") -> "list[PipelineResult]":
        """Store *results* and return those that are new or changed status.

        The first save for each provider only records a baseline and returns
        nothing, so existing runs don't trigger a burst of notifications on
        startup.
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

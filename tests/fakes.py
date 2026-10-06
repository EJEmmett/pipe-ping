"""In-memory plugin doubles for exercising the daemon."""

from datetime import UTC, datetime

from pipe_ping.models.provider import PipelineResult, PipelineStatus

_EPOCH = datetime(2000, 1, 1, tzinfo=UTC)

_DEFAULT_RESULTS: "list[PipelineResult]" = [
    PipelineResult(
        id="phony-1",
        provider="phony",
        repo="org/repo",
        branch="main",
        commit_sha="abc0000000000000000000000000000000000001",
        status=PipelineStatus.SUCCESS,
        url="https://ci.example.com/pipelines/1",
        created_at=_EPOCH,
        started_at=_EPOCH,
        finished_at=_EPOCH,
        raw={},
    ),
    PipelineResult(
        id="phony-2",
        provider="phony",
        repo="org/repo",
        branch="feature",
        commit_sha="abc0000000000000000000000000000000000002",
        status=PipelineStatus.FAILURE,
        url="https://ci.example.com/pipelines/2",
        created_at=_EPOCH,
        started_at=_EPOCH,
        finished_at=_EPOCH,
        raw={},
    ),
    PipelineResult(
        id="phony-3",
        provider="phony",
        repo="org/repo",
        branch="develop",
        commit_sha="abc0000000000000000000000000000000000003",
        status=PipelineStatus.RUNNING,
        url="https://ci.example.com/pipelines/3",
        created_at=_EPOCH,
        started_at=_EPOCH,
        finished_at=None,
        raw={},
    ),
]


class PhonyProvider:
    results: "list[PipelineResult]"

    def __init__(self) -> None:
        self.results = list(_DEFAULT_RESULTS)

    async def setup(self) -> None: ...
    async def teardown(self) -> None: ...

    async def poll(self) -> "list[PipelineResult]":
        return list(self.results)


class NullRepository:
    """Stores nothing, so it cannot detect changes and passes every result on."""

    async def setup(self) -> None: ...
    async def teardown(self) -> None: ...

    async def save(self, results: "list[PipelineResult]") -> "list[PipelineResult]":
        return results


class PhonyNotifier:
    notified: "list[PipelineResult]"

    def __init__(self) -> None:
        self.notified = []

    async def setup(self) -> None: ...
    async def teardown(self) -> None: ...

    async def notify(self, results: "list[PipelineResult]") -> None:
        self.notified.extend(results)

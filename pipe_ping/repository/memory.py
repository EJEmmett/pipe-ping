from typing import TYPE_CHECKING

from pipe_ping.models.repository import PipelineResultDocument
from pipe_ping.repository.abstract import (
    AbstractRepository,
    AbstractTransaction,
    AbstractTransactionContext,
)

if TYPE_CHECKING:
    from types import TracebackType
    from typing import Self

    from pipe_ping.models.provider import PipelineResult


class MemoryRepository(AbstractRepository):
    @classmethod
    def create(cls) -> "Self":
        return cls()

    async def _open(self) -> None:
        self._store: dict[str, PipelineResultDocument] = {}

    async def _close(self) -> None:
        self._store.clear()

    def _transaction(self) -> "MemoryTransactionContext":
        return MemoryTransactionContext(self._store)


class MemoryTransactionContext(AbstractTransactionContext):
    def __init__(self, store: dict[str, PipelineResultDocument]) -> None:
        self._store = store

    async def __aenter__(self) -> "MemoryTransaction":
        return MemoryTransaction(self._store)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: "TracebackType | None",
    ) -> bool | None:
        pass


class MemoryTransaction(AbstractTransaction):
    def __init__(self, store: dict[str, PipelineResultDocument]) -> None:
        self._store = store

    async def write_one_pipeline_result(
        self, result: "PipelineResult"
    ) -> PipelineResultDocument:
        doc = PipelineResultDocument.from_result(result)
        self._store[doc.id] = doc
        return doc

    async def read_one_pipeline_result(
        self, pipeline_id: str
    ) -> PipelineResultDocument | None:
        return self._store.get(pipeline_id)

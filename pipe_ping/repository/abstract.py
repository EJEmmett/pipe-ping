from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import TracebackType
    from typing import Self

    from pipe_ping.models.provider import PipelineResult
    from pipe_ping.models.repository import PipelineResultDocument


class AbstractRepository(ABC):
    _opened: bool = False

    @classmethod
    @abstractmethod
    def create(cls) -> "Self": ...

    async def open(self) -> None:
        await self._open()
        self._opened = True

    async def close(self) -> None:
        self._require_open()
        await self._close()
        self._opened = False

    def transaction(self) -> "AbstractTransactionContext":
        self._require_open()
        return self._transaction()

    def _require_open(self) -> None:
        if not self._opened:
            raise RuntimeError(f"{type(self).__name__}.open() must be called first")

    @abstractmethod
    async def _open(self) -> None: ...

    @abstractmethod
    async def _close(self) -> None: ...

    @abstractmethod
    def _transaction(self) -> "AbstractTransactionContext": ...


class AbstractTransactionContext(AbstractAsyncContextManager):
    @abstractmethod
    async def __aenter__(self) -> "AbstractTransaction": ...

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: "TracebackType | None",
    ) -> bool | None: ...


class AbstractTransaction(ABC):
    @abstractmethod
    async def write_one_pipeline_result(
        self, result: "PipelineResult"
    ) -> "PipelineResultDocument": ...

    @abstractmethod
    async def read_one_pipeline_result(
        self, pipeline_id: str
    ) -> "PipelineResultDocument | None": ...

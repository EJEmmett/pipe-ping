from collections.abc import AsyncGenerator

import pytest_asyncio
from pipe_ping.repository.memory import MemoryRepository


@pytest_asyncio.fixture
async def repository() -> AsyncGenerator[MemoryRepository]:
    repo = MemoryRepository.create()
    await repo.open()
    yield repo
    await repo.close()

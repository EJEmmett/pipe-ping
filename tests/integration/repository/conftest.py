from collections.abc import AsyncGenerator

import pytest_asyncio
from pipe_ping.repository.in_memory import InMemoryRepository


@pytest_asyncio.fixture
async def repository() -> AsyncGenerator[InMemoryRepository]:
    repo = InMemoryRepository.create()
    await repo.open()
    yield repo
    await repo.close()

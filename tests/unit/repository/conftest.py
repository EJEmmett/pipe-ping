import pytest
from pipe_ping.repository.memory import MemoryTransaction


@pytest.fixture
def transaction() -> MemoryTransaction:
    return MemoryTransaction({})

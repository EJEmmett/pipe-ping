import pytest
from pipe_ping.repository.in_memory import InMemoryTransaction


@pytest.fixture
def transaction() -> InMemoryTransaction:
    return InMemoryTransaction({})

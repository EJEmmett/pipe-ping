from importlib.metadata import EntryPoint

import pytest
from pipe_ping.plugin import (
    NOTIFIER_GROUP,
    PROVIDER_GROUP,
    REPOSITORY_GROUP,
    PluginInfo,
)
from pipe_ping.plugin._impl.memory import MemoryRepository
from pipe_ping.plugin._impl.sqlite import SqliteRepository
from pipe_ping.plugin.errors import AllPluginsFailedError
from pipe_ping.tools.settings import SqliteSettings

from tests.fakes import PhonyNotifier, PhonyProvider


@pytest.fixture
def phony_provider():
    return PluginInfo(
        EntryPoint(
            name="PhonyProvider",
            value="tests.fakes:PhonyProvider",
            group=PROVIDER_GROUP,
        ),
        PhonyProvider(),
    )


@pytest.fixture
def memory_repository():
    return PluginInfo(
        EntryPoint(
            name="MemoryRepository",
            value="pipe_ping.plugin._impl.memory:MemoryRepository",
            group=REPOSITORY_GROUP,
        ),
        MemoryRepository(),
    )


@pytest.fixture
def phony_notifier():
    return PluginInfo(
        EntryPoint(
            name="PhonyNotifier",
            value="tests.fakes:PhonyNotifier",
            group=NOTIFIER_GROUP,
        ),
        PhonyNotifier(),
    )


@pytest.fixture
def sqlite_settings(tmp_path):
    return SqliteSettings(path=str(tmp_path / "pipe_ping.db"))


@pytest.fixture
async def sqlite_repository(sqlite_settings):
    """A set-up ``SqliteRepository`` backed by a fresh database file."""
    repository = SqliteRepository()
    repository.settings = sqlite_settings
    await repository.setup()

    yield repository

    await repository.teardown()


@pytest.fixture
def daemon_without_providers(monkeypatch):
    """Make ``pipe-ping daemon`` fail discovery, without configuring real logging."""

    async def start_pipe_ping():
        raise AllPluginsFailedError("no providers could be loaded")

    monkeypatch.setattr("pipe_ping.client.start_pipe_ping", start_pipe_ping)
    monkeypatch.setattr("pipe_ping.client.initialize_verbosity", lambda verbose: None)

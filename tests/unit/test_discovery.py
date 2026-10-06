from importlib.metadata import EntryPoint, EntryPoints

import pytest
from pipe_ping.plugin.discovery import select_unique_entry_point
from pipe_ping.plugin.errors import PluginIsUniqueError


@pytest.fixture
def builtin():
    return EntryPoint(
        name="SqliteRepository",
        value="pipe_ping.plugin._impl.sqlite:SqliteRepository",
        group="pipe-ping.repository",
    )


@pytest.fixture
def custom():
    return EntryPoint(
        name="PostgresRepository",
        value="pipe_ping_postgres:PostgresRepository",
        group="pipe-ping.repository",
    )


def test_builtin_is_used_when_nothing_else_is_installed(builtin):
    selected = select_unique_entry_point(EntryPoints([builtin]), builtin.group)

    assert selected == builtin


def test_custom_plugin_replaces_builtin(builtin, custom):
    selected = select_unique_entry_point(EntryPoints([builtin, custom]), builtin.group)

    assert selected == custom


def test_more_than_one_custom_plugin_names_them_all(builtin, custom):
    other = EntryPoint(
        name="RedisRepository",
        value="pipe_ping_redis:RedisRepository",
        group="pipe-ping.repository",
    )

    with pytest.raises(PluginIsUniqueError) as exc_info:
        select_unique_entry_point(EntryPoints([builtin, custom, other]), builtin.group)

    message = str(exc_info.value)
    assert "allows one plugin but 2 are installed" in message
    assert "PostgresRepository (pipe_ping_postgres:PostgresRepository)" in message
    assert "RedisRepository (pipe_ping_redis:RedisRepository)" in message
    assert "SqliteRepository" not in message

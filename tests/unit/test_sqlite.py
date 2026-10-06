import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime

import pytest
from pipe_ping.models.provider import PipelineResult, PipelineStatus
from pipe_ping.plugin._impl.sqlite import SqliteRepository


@pytest.fixture
def result():
    return PipelineResult(
        id="run-1",
        provider="github",
        repo="owner/repo",
        branch="main",
        commit_sha="abc123",
        status=PipelineStatus.RUNNING,
        url="https://github.com/owner/repo/actions/runs/1",
        created_at=datetime(2000, 1, 1, tzinfo=UTC),
        started_at=datetime(2000, 1, 1, 0, 1, tzinfo=UTC),
        finished_at=None,
        raw={"name": "CI", "nested": {"attempt": 1}},
    )


async def test_setup_creates_database_file(sqlite_repository, sqlite_settings):
    with closing(sqlite3.connect(sqlite_settings.path)) as connection:
        tables = connection.execute("SELECT name FROM sqlite_master").fetchall()

    assert ("runs",) in tables


async def test_save_before_setup_raises(sqlite_settings, result):
    repository = SqliteRepository()
    repository.settings = sqlite_settings

    with pytest.raises(RuntimeError, match="setup"):
        await repository.save([result])


async def test_save_first_poll_stores_baseline_without_changes(
    sqlite_repository, sqlite_settings, result
):
    assert await sqlite_repository.save([result]) == []

    with closing(sqlite3.connect(sqlite_settings.path)) as connection:
        row = connection.execute(
            "SELECT provider, id, status, started_at, finished_at, raw FROM runs"
        ).fetchone()

    assert row == (
        "github",
        "run-1",
        "running",
        "2000-01-01T00:01:00Z",
        None,
        json.dumps({"name": "CI", "nested": {"attempt": 1}}),
    )


async def test_save_unchanged_status_returns_nothing(sqlite_repository, result):
    await sqlite_repository.save([result])

    assert await sqlite_repository.save([result]) == []


@pytest.mark.parametrize(
    "status",
    [
        PipelineStatus.SUCCESS,
        PipelineStatus.FAILURE,
        PipelineStatus.CANCELLED,
    ],
)
async def test_save_status_change_is_returned(sqlite_repository, result, status):
    await sqlite_repository.save([result])
    updated = result.model_copy(update={"status": status})

    assert await sqlite_repository.save([updated]) == [updated]


async def test_save_new_run_after_baseline_is_returned(sqlite_repository, result):
    await sqlite_repository.save([result])
    new_run = result.model_copy(update={"id": "run-2"})

    assert await sqlite_repository.save([result, new_run]) == [new_run]


async def test_save_baseline_is_per_provider(sqlite_repository, result):
    await sqlite_repository.save([result])
    other = result.model_copy(update={"provider": "gitlab"})

    assert await sqlite_repository.save([other]) == []


async def test_save_same_id_different_provider_does_not_collide(
    sqlite_repository, sqlite_settings, result
):
    other = result.model_copy(update={"provider": "gitlab"})

    await sqlite_repository.save([result, other])

    with closing(sqlite3.connect(sqlite_settings.path)) as connection:
        rows = connection.execute(
            "SELECT provider, id FROM runs ORDER BY provider"
        ).fetchall()

    assert rows == [("github", "run-1"), ("gitlab", "run-1")]


async def test_changes_while_stopped_are_reported_after_restart(
    sqlite_repository, sqlite_settings, result
):
    await sqlite_repository.save([result])
    await sqlite_repository.teardown()

    restarted = SqliteRepository()
    restarted.settings = sqlite_settings
    await restarted.setup()
    finished = result.model_copy(update={"status": PipelineStatus.FAILURE})

    try:
        assert await restarted.save([finished]) == [finished]
    finally:
        await restarted.teardown()

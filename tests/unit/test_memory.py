from datetime import UTC, datetime

import pytest
from pipe_ping.models.provider import PipelineResult, PipelineStatus
from pipe_ping.plugin._impl.memory import MemoryRepository


@pytest.fixture
def repository():
    return MemoryRepository()


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
        started_at=None,
        finished_at=None,
        raw={},
    )


async def test_save_first_poll_stores_baseline_without_changes(repository, result):
    assert await repository.save([result]) == []
    assert repository.results == {("github", "run-1"): result}


async def test_save_unchanged_status_returns_nothing(repository, result):
    await repository.save([result])

    assert await repository.save([result.model_copy()]) == []


@pytest.mark.parametrize(
    "status",
    [
        PipelineStatus.SUCCESS,
        PipelineStatus.FAILURE,
        PipelineStatus.CANCELLED,
    ],
)
async def test_save_status_change_is_returned(repository, result, status):
    await repository.save([result])
    updated = result.model_copy(update={"status": status})

    assert await repository.save([updated]) == [updated]
    assert repository.results[("github", "run-1")] is updated


async def test_save_new_run_after_baseline_is_returned(repository, result):
    await repository.save([result])
    new_run = result.model_copy(update={"id": "run-2"})

    assert await repository.save([result, new_run]) == [new_run]


async def test_save_baseline_is_per_provider(repository, result):
    await repository.save([result])
    other = result.model_copy(update={"provider": "gitlab"})

    assert await repository.save([other]) == []


async def test_save_same_id_different_provider_does_not_collide(repository, result):
    other = result.model_copy(update={"provider": "gitlab"})

    await repository.save([result, other])

    assert repository.results == {
        ("github", "run-1"): result,
        ("gitlab", "run-1"): other,
    }


async def test_save_empty_poll_does_not_set_baseline(repository, result):
    await repository.save([])

    assert await repository.save([result]) == []

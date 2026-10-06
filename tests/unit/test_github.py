from datetime import UTC, datetime

import pytest
from pipe_ping.models.provider import PipelineStatus
from pipe_ping.plugin._impl.github import GitHubProvider, map_run_status
from pipe_ping.plugin.errors import PluginUnavailableError
from pipe_ping.tools.settings import GitHubSettings
from pydantic import SecretStr


@pytest.fixture
def workflow_run():
    """A single run as returned by ``GET /repos/{owner}/{repo}/actions/runs``."""
    return {
        "id": 30433642,
        "name": "CI",
        "head_branch": "main",
        "head_sha": "acb5820ced9479c074f688cc328bf03f341a511d",
        "event": "push",
        "status": "completed",
        "conclusion": "success",
        "html_url": "https://github.com/owner/repo/actions/runs/30433642",
        "created_at": "2026-10-06T12:00:00Z",
        "updated_at": "2026-10-06T12:05:00Z",
        "run_started_at": "2026-10-06T12:00:05Z",
        "repository": {"full_name": "owner/repo"},
    }


@pytest.fixture
def settings(github_api):
    return GitHubSettings(
        token=SecretStr("test-token"), repos=["owner/repo"], api_url=github_api.url
    )


@pytest.fixture
async def provider(settings):
    provider = GitHubProvider()
    provider.settings = settings
    yield provider
    await provider.teardown()


@pytest.mark.parametrize(
    ("status", "conclusion", "expected"),
    [
        ("requested", None, PipelineStatus.PENDING),
        ("queued", None, PipelineStatus.PENDING),
        ("pending", None, PipelineStatus.PENDING),
        ("waiting", None, PipelineStatus.PENDING),
        ("in_progress", None, PipelineStatus.RUNNING),
        ("completed", "success", PipelineStatus.SUCCESS),
        ("completed", "failure", PipelineStatus.FAILURE),
        ("completed", "timed_out", PipelineStatus.FAILURE),
        ("completed", "startup_failure", PipelineStatus.FAILURE),
        ("completed", "cancelled", PipelineStatus.CANCELLED),
        ("completed", "skipped", PipelineStatus.SKIPPED),
        ("completed", "neutral", PipelineStatus.UNKNOWN),
        ("completed", "stale", PipelineStatus.UNKNOWN),
        ("completed", "action_required", PipelineStatus.UNKNOWN),
        ("completed", None, PipelineStatus.UNKNOWN),
        ("something_new", None, PipelineStatus.UNKNOWN),
        (None, None, PipelineStatus.UNKNOWN),
    ],
)
def test_map_run_status(status, conclusion, expected):
    assert map_run_status(status, conclusion) is expected


async def test_setup_raises_without_token(provider, settings):
    settings.token = None

    with pytest.raises(PluginUnavailableError, match="PIPE_PING_GITHUB__TOKEN"):
        await provider.setup()


async def test_setup_raises_without_repos(provider, settings):
    settings.repos = []

    with pytest.raises(PluginUnavailableError, match="PIPE_PING_GITHUB__REPOS"):
        await provider.setup()


async def test_poll_before_setup_raises(provider):
    with pytest.raises(RuntimeError, match="setup"):
        await provider.fetch_runs("owner/repo")


async def test_poll_sends_authenticated_request(provider, github_api, workflow_run):
    github_api.runs["owner/repo"] = [workflow_run]
    await provider.setup()

    await provider.poll()

    [request] = github_api.requests
    assert request.path == "/repos/owner/repo/actions/runs"
    assert request.query == {"per_page": "20"}
    assert request.headers["Authorization"] == "Bearer test-token"
    assert request.headers["Accept"] == "application/vnd.github+json"
    assert request.headers["X-GitHub-Api-Version"] == "2022-11-28"


async def test_poll_converts_completed_run(provider, github_api, workflow_run):
    github_api.runs["owner/repo"] = [workflow_run]
    await provider.setup()

    [result] = await provider.poll()

    assert result.id == "30433642"
    assert result.provider == "github"
    assert result.repo == "owner/repo"
    assert result.branch == "main"
    assert result.commit_sha == "acb5820ced9479c074f688cc328bf03f341a511d"
    assert result.status is PipelineStatus.SUCCESS
    assert result.url == "https://github.com/owner/repo/actions/runs/30433642"
    assert result.created_at == datetime(2026, 10, 6, 12, 0, tzinfo=UTC)
    assert result.started_at == datetime(2026, 10, 6, 12, 0, 5, tzinfo=UTC)
    assert result.finished_at == datetime(2026, 10, 6, 12, 5, tzinfo=UTC)
    assert result.raw["name"] == "CI"


async def test_poll_in_progress_run_has_no_finish_time(
    provider, github_api, workflow_run
):
    workflow_run["status"] = "in_progress"
    workflow_run["conclusion"] = None
    github_api.runs["owner/repo"] = [workflow_run]
    await provider.setup()

    [result] = await provider.poll()

    assert result.status is PipelineStatus.RUNNING
    assert result.finished_at is None


async def test_poll_combines_repos(provider, settings, github_api, workflow_run):
    settings.repos = ["owner/repo", "owner/other"]
    github_api.runs["owner/repo"] = [workflow_run]
    github_api.runs["owner/other"] = [workflow_run]
    await provider.setup()

    results = await provider.poll()

    assert [result.repo for result in results] == ["owner/repo", "owner/other"]


async def test_poll_skips_failing_repo(
    provider, settings, github_api, workflow_run, caplog
):
    settings.repos = ["owner/repo", "owner/missing"]
    github_api.runs["owner/repo"] = [workflow_run]
    await provider.setup()

    results = await provider.poll()

    assert [result.repo for result in results] == ["owner/repo"]
    assert "Polling owner/missing failed" in caplog.text

from datetime import UTC, datetime

import pytest
from pipe_ping.models.provider import PipelineStatus
from pipe_ping.plugin._impl.gitlab import GitLabProvider, map_pipeline_status
from pipe_ping.plugin.errors import PluginUnavailableError
from pipe_ping.tools.settings import GitLabSettings
from pydantic import SecretStr


@pytest.fixture
def pipeline():
    """A single pipeline as returned by ``GET /projects/:id/pipelines``."""
    return {
        "id": 47,
        "iid": 12,
        "project_id": 29,
        "status": "success",
        "source": "push",
        "ref": "main",
        "sha": "a91957a858320c0e17f3a0eca7cfacbff50ea29a",
        "web_url": "https://gitlab.com/group/project/-/pipelines/47",
        "created_at": "2026-10-06T12:00:00.000Z",
        "updated_at": "2026-10-06T12:05:00.000Z",
    }


@pytest.fixture
def settings(gitlab_api):
    return GitLabSettings(
        token=SecretStr("test-token"),
        projects=["group/project"],
        api_url=gitlab_api.url,
    )


@pytest.fixture
async def provider(settings):
    provider = GitLabProvider()
    provider.settings = settings
    yield provider
    await provider.teardown()


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("created", PipelineStatus.PENDING),
        ("waiting_for_resource", PipelineStatus.PENDING),
        ("preparing", PipelineStatus.PENDING),
        ("pending", PipelineStatus.PENDING),
        ("scheduled", PipelineStatus.PENDING),
        ("manual", PipelineStatus.PENDING),
        ("running", PipelineStatus.RUNNING),
        ("canceling", PipelineStatus.RUNNING),
        ("success", PipelineStatus.SUCCESS),
        ("failed", PipelineStatus.FAILURE),
        ("canceled", PipelineStatus.CANCELLED),
        ("skipped", PipelineStatus.SKIPPED),
        ("something_new", PipelineStatus.UNKNOWN),
        (None, PipelineStatus.UNKNOWN),
    ],
)
def test_map_pipeline_status(status, expected):
    assert map_pipeline_status(status) is expected


async def test_setup_raises_without_token(provider, settings):
    settings.token = None

    with pytest.raises(PluginUnavailableError, match="PIPE_PING_GITLAB__TOKEN"):
        await provider.setup()


async def test_setup_raises_without_projects(provider, settings):
    settings.projects = []

    with pytest.raises(PluginUnavailableError, match="PIPE_PING_GITLAB__PROJECTS"):
        await provider.setup()


async def test_poll_before_setup_raises(provider):
    with pytest.raises(RuntimeError, match="setup"):
        await provider.fetch_pipelines("group/project")


async def test_poll_sends_authenticated_request(provider, gitlab_api, pipeline):
    gitlab_api.pipelines["group/project"] = [pipeline]
    await provider.setup()

    await provider.poll()

    [request] = gitlab_api.requests
    assert request.path == "/projects/group%2Fproject/pipelines"
    assert request.query == {"per_page": "20"}
    assert request.headers["PRIVATE-TOKEN"] == "test-token"


async def test_poll_converts_finished_pipeline(provider, gitlab_api, pipeline):
    gitlab_api.pipelines["group/project"] = [pipeline]
    await provider.setup()

    [result] = await provider.poll()

    assert result.id == "47"
    assert result.provider == "gitlab"
    assert result.repo == "group/project"
    assert result.branch == "main"
    assert result.commit_sha == "a91957a858320c0e17f3a0eca7cfacbff50ea29a"
    assert result.status is PipelineStatus.SUCCESS
    assert result.url == "https://gitlab.com/group/project/-/pipelines/47"
    assert result.created_at == datetime(2026, 10, 6, 12, 0, tzinfo=UTC)
    assert result.started_at is None
    assert result.finished_at == datetime(2026, 10, 6, 12, 5, tzinfo=UTC)
    assert result.raw["source"] == "push"


async def test_poll_running_pipeline_has_no_finish_time(provider, gitlab_api, pipeline):
    pipeline["status"] = "running"
    gitlab_api.pipelines["group/project"] = [pipeline]
    await provider.setup()

    [result] = await provider.poll()

    assert result.status is PipelineStatus.RUNNING
    assert result.finished_at is None


async def test_poll_combines_projects(provider, settings, gitlab_api, pipeline):
    settings.projects = ["group/project", "group/subgroup/other"]
    gitlab_api.pipelines["group/project"] = [pipeline]
    gitlab_api.pipelines["group/subgroup/other"] = [pipeline]
    await provider.setup()

    results = await provider.poll()

    assert [result.repo for result in results] == [
        "group/project",
        "group/subgroup/other",
    ]


async def test_poll_skips_failing_project(
    provider, settings, gitlab_api, pipeline, caplog
):
    settings.projects = ["group/project", "group/missing"]
    gitlab_api.pipelines["group/project"] = [pipeline]
    await provider.setup()

    results = await provider.poll()

    assert [result.repo for result in results] == ["group/project"]
    assert "Polling group/missing failed" in caplog.text

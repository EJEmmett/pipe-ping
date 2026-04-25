from unittest.mock import AsyncMock, Mock

import pytest
from aiohttp import ClientError, ClientResponse, ClientSession
from aioresponses import aioresponses as mock_aiohttp
from pipe_ping.models import PipelineStatus
from pipe_ping.models.provider import PipelineResult
from pipe_ping.provider.errors import (
    PipePingProviderAuthenticationError,
    PipePingProviderMisconfiguredError,
)
from pipe_ping.provider.github import (
    ENDPOINT,
    WorkflowRun,
    _check_response,
    _fetch_repo,
    _map_status,
    _map_workflow_run,
    _parse_response,
    github_provider,
)

REPO = "owner/repo"
REPO_ENDPOINT = ENDPOINT.format(owner_repo=REPO)


@pytest.fixture
def valid_run() -> WorkflowRun:
    return {
        "id": 42,
        "status": "completed",
        "conclusion": "success",
        "head_branch": "main",
        "head_sha": "a" * 40,
        "html_url": "https://github.com/owner/repo/actions/runs/42",
        "created_at": "2026-04-24T12:00:00Z",
        "updated_at": "2026-04-24T12:01:00Z",
        "run_started_at": "2026-04-24T12:00:05Z",
    }


@pytest.fixture
def test_headers() -> dict[str, str]:
    return {
        "Authorization": "Bearer ghp_test",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


@pytest.fixture
def mock_response() -> Mock:
    return Mock(spec_set=ClientResponse)


@pytest.fixture
def mock_settings(monkeypatch: pytest.MonkeyPatch) -> Mock:
    mock_settings = Mock(
        token=Mock(get_secret_value=Mock(return_value="ghp_test")),
        repos=[],
    )

    monkeypatch.setattr(
        "pipe_ping.provider.github._get_settings", lambda: mock_settings
    )
    return mock_settings


class TestMapStatus:
    @pytest.mark.parametrize(
        ("status", "conclusion", "expected"),
        [
            ("queued", None, PipelineStatus.PENDING),
            ("in_progress", None, PipelineStatus.RUNNING),
            ("completed", "success", PipelineStatus.SUCCESS),
            ("completed", "failure", PipelineStatus.FAILURE),
            ("completed", "timed_out", PipelineStatus.FAILURE),
            ("completed", "cancelled", PipelineStatus.CANCELLED),
            ("completed", "skipped", PipelineStatus.SKIPPED),
            ("completed", "action_required", PipelineStatus.UNKNOWN),
            ("completed", "neutral", PipelineStatus.UNKNOWN),
            ("unknown_status", None, PipelineStatus.UNKNOWN),
        ],
    )
    def test_maps_github_status_and_conclusion(
        self,
        status: str | None,
        conclusion: str | None,
        expected: PipelineStatus,
    ) -> None:
        assert _map_status(status, conclusion) == expected


class TestMapWorkflowRun:
    def test_null_branch_falls_back_to_short_sha(self, valid_run: WorkflowRun) -> None:
        valid_run["head_branch"] = None
        result = _map_workflow_run(REPO, valid_run)
        assert result.branch == valid_run["head_sha"][:7]

    def test_absent_run_started_at_gives_none_started_at(
        self, valid_run: WorkflowRun
    ) -> None:
        del valid_run["run_started_at"]
        result = _map_workflow_run(REPO, valid_run)
        assert result.started_at is None

    def test_null_conclusion_gives_none_finished_at(
        self, valid_run: WorkflowRun
    ) -> None:
        valid_run["conclusion"] = None
        result = _map_workflow_run(REPO, valid_run)
        assert result.finished_at is None


class TestCheckResponse:
    @pytest.mark.parametrize("status", [200, 201])
    def test_success_status_returns_true(
        self, status: int, mock_response: Mock
    ) -> None:
        mock_response.status = status

        assert _check_response(mock_response, REPO) is True

    @pytest.mark.parametrize("status", [401, 403])
    def test_auth_status_raises_auth_error(
        self, status: int, mock_response: Mock
    ) -> None:
        mock_response.status = status
        with pytest.raises(
            PipePingProviderAuthenticationError, match="PIPE_PING_GITHUB_TOKEN"
        ):
            _check_response(mock_response, REPO)

    @pytest.mark.parametrize("status", [429, 500, 503, 302, 404])
    def test_non_success_status_returns_false(
        self, status: int, mock_response: Mock
    ) -> None:
        mock_response.status = status

        assert _check_response(mock_response, REPO) is False


class TestParseResponse:
    async def test_valid_run_yields_pipeline_result(
        self, mock_response: Mock, valid_run: WorkflowRun
    ) -> None:
        mock_response.json = AsyncMock(return_value={"workflow_runs": [valid_run]})

        results = [item async for item in _parse_response(mock_response, REPO)]
        assert len(results) == 1
        assert isinstance(results[0], PipelineResult)

    async def test_multiple_valid_runs_yields_all(
        self, mock_response: Mock, valid_run: WorkflowRun
    ) -> None:
        mock_response.json = AsyncMock(
            return_value={"workflow_runs": [valid_run, {**valid_run, "id": 43}]}
        )

        results = [item async for item in _parse_response(mock_response, REPO)]
        assert len(results) == 2

    @pytest.mark.parametrize(
        "body",
        [
            ["unexpected"],
            {"something_else": []},
        ],
    )
    async def test_bad_body_shape_yields_nothing(
        self, mock_response: Mock, body: object
    ) -> None:
        mock_response.json = AsyncMock(return_value=body)

        results = [item async for item in _parse_response(mock_response, REPO)]
        assert results == []

    async def test_malformed_run_is_skipped(self, mock_response: Mock) -> None:
        mock_response.json = AsyncMock(
            return_value={"workflow_runs": [{"invalid": "run"}]}
        )

        results = [item async for item in _parse_response(mock_response, REPO)]
        assert results == []

    async def test_valid_run_after_malformed_is_yielded(
        self, mock_response: Mock, valid_run: WorkflowRun
    ) -> None:
        mock_response.json = AsyncMock(
            return_value={"workflow_runs": [{"invalid": "run"}, valid_run]}
        )

        results = [item async for item in _parse_response(mock_response, REPO)]
        assert len(results) == 1
        assert results[0].id == "42"


class TestFetchRepo:
    async def test_200_returns_pipeline_results(
        self, valid_run: WorkflowRun, test_headers: dict[str, str]
    ) -> None:
        with mock_aiohttp() as m:
            m.get(REPO_ENDPOINT, payload={"workflow_runs": [valid_run]})
            async with ClientSession() as session:
                results = await _fetch_repo(session, test_headers, REPO)

        assert len(results) == 1
        assert isinstance(results[0], PipelineResult)

    async def test_401_propagates_auth_error(
        self, test_headers: dict[str, str]
    ) -> None:
        with mock_aiohttp() as m:
            m.get(REPO_ENDPOINT, status=401)
            async with ClientSession() as session:
                with pytest.raises(PipePingProviderAuthenticationError):
                    await _fetch_repo(session, test_headers, REPO)

    @pytest.mark.parametrize("status", [429, 500])
    async def test_error_status_returns_empty_list(
        self, status: int, test_headers: dict[str, str]
    ) -> None:
        with mock_aiohttp() as m:
            m.get(REPO_ENDPOINT, status=status)
            async with ClientSession() as session:
                results = await _fetch_repo(session, test_headers, REPO)

        assert results == []

    async def test_network_error_returns_empty_list(
        self, test_headers: dict[str, str]
    ) -> None:
        with mock_aiohttp() as m:
            m.get(REPO_ENDPOINT, exception=ClientError())
            async with ClientSession() as session:
                results = await _fetch_repo(session, test_headers, REPO)

        assert results == []


class TestGithubProvider:
    async def test_no_repos_raises_misconfigured_error(
        self,
        mock_settings,
    ) -> None:
        async with ClientSession() as session:
            with pytest.raises(PipePingProviderMisconfiguredError):
                await github_provider(session)

    async def test_returns_results_for_configured_repo(
        self,
        mock_settings,
        valid_run: WorkflowRun,
    ) -> None:
        mock_settings.repos = [REPO]

        with mock_aiohttp() as m:
            m.get(REPO_ENDPOINT, payload={"workflow_runs": [valid_run]})
            async with ClientSession() as session:
                results = await github_provider(session)

        assert len(results) == 1
        assert results[0].repo == REPO

    async def test_multiple_repos_results_are_flattened(
        self,
        mock_settings,
        valid_run: WorkflowRun,
    ) -> None:
        repo2 = "owner/other"
        endpoint2 = ENDPOINT.format(owner_repo=repo2)
        run2 = {**valid_run, "id": 99}
        mock_settings.repos = [REPO, repo2]

        with mock_aiohttp() as m:
            m.get(REPO_ENDPOINT, payload={"workflow_runs": [valid_run]})
            m.get(endpoint2, payload={"workflow_runs": [run2]})
            async with ClientSession() as session:
                results = await github_provider(session)

        assert len(results) == 2
        assert {r.repo for r in results} == {REPO, repo2}

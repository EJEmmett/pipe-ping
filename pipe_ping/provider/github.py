import logging
from asyncio import TaskGroup
from collections.abc import AsyncGenerator
from datetime import datetime
from functools import lru_cache
from typing import Any, NotRequired, TypedDict, cast

from aiohttp import ClientError, ClientResponse, ClientSession
from pydantic import Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from pipe_ping.fields import CommaSeparatedList
from pipe_ping.models import PipelineStatus
from pipe_ping.models.provider import PipelineResult
from pipe_ping.provider.errors import (
    PipePingProviderAuthenticationError,
    PipePingProviderMisconfiguredError,
)

module_logger = logging.getLogger(__name__)

PROVIDER_NAME = "github"
ENDPOINT = "https://api.github.com/repos/{owner_repo}/actions/runs"


class GitHubSettings(BaseSettings):
    token: SecretStr = Field(...)
    repos: CommaSeparatedList = []

    model_config = SettingsConfigDict(
        env_prefix="PIPE_PING_GITHUB_",
        env_file=".env",
    )


@lru_cache(maxsize=1)
def _get_settings() -> GitHubSettings:
    return GitHubSettings()


class WorkflowRun(TypedDict):
    id: int
    status: str | None
    conclusion: str | None
    head_branch: str | None
    head_sha: str
    html_url: str
    created_at: str
    updated_at: str
    run_started_at: NotRequired[str]


class WorkflowRunsResponse(TypedDict):
    workflow_runs: list[WorkflowRun]
    total_count: int


def _map_status(status: str | None, conclusion: str | None) -> PipelineStatus:
    match (status, conclusion):
        case ("queued", _):
            return PipelineStatus.PENDING
        case ("in_progress", _):
            return PipelineStatus.RUNNING
        case ("completed", "success"):
            return PipelineStatus.SUCCESS
        case ("completed", "failure") | ("completed", "timed_out"):
            return PipelineStatus.FAILURE
        case ("completed", "cancelled"):
            return PipelineStatus.CANCELLED
        case ("completed", "skipped"):
            return PipelineStatus.SKIPPED
        case _:
            return PipelineStatus.UNKNOWN


def _map_workflow_run(repo: str, workflow_run: WorkflowRun) -> PipelineResult:
    branch = workflow_run["head_branch"] or workflow_run["head_sha"][:7]
    status = _map_status(workflow_run["status"], workflow_run["conclusion"])

    created_at = datetime.fromisoformat(workflow_run["created_at"])
    updated_at = datetime.fromisoformat(workflow_run["updated_at"])

    run_started_at = workflow_run.get("run_started_at")
    started_at = (
        datetime.fromisoformat(run_started_at) if run_started_at is not None else None
    )

    finished_at = updated_at if workflow_run["conclusion"] is not None else None

    return PipelineResult(
        id=str(workflow_run["id"]),
        provider=PROVIDER_NAME,
        repo=repo,
        branch=branch,
        commit_sha=workflow_run["head_sha"],
        status=status,
        url=workflow_run["html_url"],
        created_at=created_at,
        started_at=started_at,
        finished_at=finished_at,
        raw=cast("dict[str, Any]", workflow_run),
    )


def _check_response(response: ClientResponse, repo: str) -> bool:
    log_extra = {"repo": repo, "http_status": response.status}

    match response.status:
        case 401 | 403:
            module_logger.error(
                "GitHub authentication failed for %s (HTTP %d) — "
                "check PIPE_PING_GITHUB_TOKEN",
                repo,
                response.status,
                extra=log_extra,
            )
            raise PipePingProviderAuthenticationError(
                f"GitHub rejected credentials for {repo} "
                f"(HTTP {response.status}): check PIPE_PING_GITHUB_TOKEN"
            )
        case 429:
            module_logger.warning(
                "GitHub rate limit exceeded for %s — skipping this cycle",
                repo,
                extra=log_extra,
            )
            return False
        case code if code >= 500:
            module_logger.warning(
                "GitHub server error for %s (HTTP %d) — skipping this cycle",
                repo,
                response.status,
                extra=log_extra,
            )
            return False
        case code if 200 <= code < 300:
            return True
        case _:
            module_logger.warning(
                "GitHub unexpected status for %s (HTTP %d) — skipping this cycle",
                repo,
                response.status,
                extra=log_extra,
            )
            return False


async def _parse_response(
    response: ClientResponse,
    repo: str,
) -> AsyncGenerator[PipelineResult]:
    log_extra = {"repo": repo}

    raw_body = await response.json()
    if not isinstance(raw_body, dict):
        type_name = type(raw_body).__name__

        module_logger.warning(
            "Unexpected response shape from GitHub for %s: expected dict, got %s",
            repo,
            type_name,
            extra=log_extra | {"body_type": type_name},
        )
        return

    body = cast("WorkflowRunsResponse", raw_body)
    try:
        workflow_runs = body["workflow_runs"]
    except KeyError:
        module_logger.warning(
            "GitHub response for %s missing 'workflow_runs' key — "
            "API shape may have changed",
            repo,
            extra=log_extra,
        )
        return

    for workflow_run in workflow_runs:
        try:
            yield _map_workflow_run(repo, workflow_run)
        except (ValidationError, KeyError):
            module_logger.warning(
                "Skipping malformed workflow run from %s: failed validation",
                repo,
                extra=log_extra | {"run_id": workflow_run.get("id")},
            )


async def _fetch_repo(
    session: ClientSession,
    headers: dict[str, str],
    repo: str,
) -> list[PipelineResult]:
    log_extra = {"repo": repo}
    try:
        async with session.get(
            ENDPOINT.format(owner_repo=repo),
            headers=headers,
        ) as response:
            if _check_response(response, repo):
                return [
                    pipeline_result
                    async for pipeline_result in _parse_response(response, repo)
                ]
    except ClientError:
        module_logger.exception(
            "Network error fetching workflow runs for %s — skipping",
            repo,
            extra=log_extra,
        )

    return []


async def github_provider(
    session: ClientSession,
) -> list[PipelineResult]:
    settings = _get_settings()

    if not settings.repos:
        module_logger.warning(
            "No repos configured for GitHub provider — set PIPE_PING_GITHUB_REPOS"
        )
        raise PipePingProviderMisconfiguredError(
            "GitHub provider has no repos to watch — set PIPE_PING_GITHUB_REPOS"
        )

    headers = {
        "Authorization": f"Bearer {settings.token.get_secret_value()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    async with TaskGroup() as tg:
        tasks = [
            tg.create_task(_fetch_repo(session, headers, repo))
            for repo in settings.repos
        ]

    return [pipeline_result for task in tasks for pipeline_result in task.result()]

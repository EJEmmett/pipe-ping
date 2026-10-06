import asyncio
import logging
from typing import TYPE_CHECKING, Any

import aiohttp

from pipe_ping.models.provider import PipelineResult, PipelineStatus
from pipe_ping.plugin.errors import PluginUnavailableError
from pipe_ping.tools import get_settings

if TYPE_CHECKING:
    from pipe_ping.tools.settings import GitHubSettings

module_logger = logging.getLogger(__name__)

_STATUS_MAP: dict[str, PipelineStatus] = {
    "requested": PipelineStatus.PENDING,
    "queued": PipelineStatus.PENDING,
    "pending": PipelineStatus.PENDING,
    "waiting": PipelineStatus.PENDING,
    "in_progress": PipelineStatus.RUNNING,
}

_CONCLUSION_MAP: dict[str, PipelineStatus] = {
    "success": PipelineStatus.SUCCESS,
    "failure": PipelineStatus.FAILURE,
    "timed_out": PipelineStatus.FAILURE,
    "startup_failure": PipelineStatus.FAILURE,
    "cancelled": PipelineStatus.CANCELLED,
    "skipped": PipelineStatus.SKIPPED,
}


def map_run_status(status: str | None, conclusion: str | None) -> PipelineStatus:
    """Map a workflow run's ``status`` and ``conclusion`` to a single status.

    GitHub sets ``conclusion`` only once ``status`` is ``completed``. Conclusions
    that are neither a pass nor a fail (``neutral``, ``stale``, ``action_required``)
    map to ``UNKNOWN``.
    """
    if status == "completed":
        return _CONCLUSION_MAP.get(conclusion or "", PipelineStatus.UNKNOWN)

    return _STATUS_MAP.get(status or "", PipelineStatus.UNKNOWN)


def to_pipeline_result(repo: str, run: "dict[str, Any]") -> PipelineResult:
    """Convert a workflow run from the GitHub API to a :class:`PipelineResult`.

    GitHub does not report when a workflow run finished, so ``updated_at`` is
    used as ``finished_at`` for completed workflow runs.
    """
    is_completed = run["status"] == "completed"

    return PipelineResult.model_validate(
        {
            "id": str(run["id"]),
            "provider": "github",
            "repo": repo,
            "branch": run["head_branch"] or "",
            "commit_sha": run["head_sha"],
            "status": map_run_status(run["status"], run["conclusion"]),
            "url": run["html_url"],
            "created_at": run["created_at"],
            "started_at": run.get("run_started_at"),
            "finished_at": run["updated_at"] if is_completed else None,
            "raw": run,
        }
    )


class GitHubProvider:
    """Fetch GitHub Actions workflow runs for each configured repository.

    Configured with ``PIPE_PING_GITHUB__TOKEN`` and ``PIPE_PING_GITHUB__REPOS``
    (a JSON list such as ``["owner/repo"]``).
    """

    settings: "GitHubSettings"
    session: aiohttp.ClientSession | None

    def __init__(self) -> None:
        self.settings = get_settings().github
        self.session = None

    async def setup(self) -> None:
        if self.settings.token is None:
            raise PluginUnavailableError(
                "Set PIPE_PING_GITHUB__TOKEN to enable the GitHub provider"
            )
        if not self.settings.repos:
            raise PluginUnavailableError(
                "Set PIPE_PING_GITHUB__REPOS to a JSON list of repositories to monitor"
            )

        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self.settings.token.get_secret_value()}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "pipe-ping",
            },
            timeout=aiohttp.ClientTimeout(total=30),
        )

    async def teardown(self) -> None:
        if self.session is not None:
            await self.session.close()

    async def poll(self) -> list[PipelineResult]:
        """Fetch recent workflow runs for every repository concurrently.

        If a repository cannot be fetched, the error is logged and the other
        repositories' results are still returned.
        """
        repos = self.settings.repos
        outcomes = await asyncio.gather(
            *(self.fetch_runs(repo) for repo in repos), return_exceptions=True
        )

        results: list[PipelineResult] = []
        for repo, outcome in zip(repos, outcomes, strict=True):
            if isinstance(outcome, BaseException):
                module_logger.error(
                    "Polling %s failed", repo, exc_info=outcome, extra={"repo": repo}
                )
                continue
            results.extend(outcome)

        return results

    async def fetch_runs(self, repo: str) -> list[PipelineResult]:
        if self.session is None:
            raise RuntimeError("GitHubProvider.setup() must be called before polling")

        url = f"{self.settings.api_url}/repos/{repo}/actions/runs"
        params = {"per_page": self.settings.runs_per_repo}
        async with self.session.get(url, params=params) as response:
            response.raise_for_status()
            payload = await response.json()

        return [to_pipeline_result(repo, run) for run in payload["workflow_runs"]]

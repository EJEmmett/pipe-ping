import asyncio
import logging
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

import aiohttp

from pipe_ping.models.provider import PipelineResult, PipelineStatus
from pipe_ping.plugin.errors import PluginUnavailableError
from pipe_ping.tools import get_settings

if TYPE_CHECKING:
    from pipe_ping.tools.settings import GitLabSettings

module_logger = logging.getLogger(__name__)

_STATUS_MAP: dict[str, PipelineStatus] = {
    "created": PipelineStatus.PENDING,
    "waiting_for_resource": PipelineStatus.PENDING,
    "preparing": PipelineStatus.PENDING,
    "pending": PipelineStatus.PENDING,
    "scheduled": PipelineStatus.PENDING,
    "manual": PipelineStatus.PENDING,
    "running": PipelineStatus.RUNNING,
    "canceling": PipelineStatus.RUNNING,
    "success": PipelineStatus.SUCCESS,
    "failed": PipelineStatus.FAILURE,
    "canceled": PipelineStatus.CANCELLED,
    "skipped": PipelineStatus.SKIPPED,
}

_FINISHED_STATUSES = frozenset({"success", "failed", "canceled", "skipped"})


def map_pipeline_status(status: str | None) -> PipelineStatus:
    """Map a pipeline's ``status`` to a :class:`PipelineStatus`.

    ``manual`` pipelines are waiting for someone to start a job, so they map to
    ``PENDING``. ``canceling`` pipelines are still stopping their jobs, so they
    map to ``RUNNING``.
    """
    return _STATUS_MAP.get(status or "", PipelineStatus.UNKNOWN)


def to_pipeline_result(project: str, pipeline: "dict[str, Any]") -> PipelineResult:
    """Convert a pipeline from the GitLab API to a :class:`PipelineResult`.

    The list pipelines endpoint does not include start or finish times, so
    ``started_at`` is ``None`` and ``updated_at`` is used as ``finished_at`` for
    finished pipelines.
    """
    is_finished = pipeline["status"] in _FINISHED_STATUSES

    return PipelineResult.model_validate(
        {
            "id": str(pipeline["id"]),
            "provider": "gitlab",
            "repo": project,
            "branch": pipeline["ref"] or "",
            "commit_sha": pipeline["sha"],
            "status": map_pipeline_status(pipeline["status"]),
            "url": pipeline["web_url"],
            "created_at": pipeline["created_at"],
            "started_at": pipeline.get("started_at"),
            "finished_at": pipeline["updated_at"] if is_finished else None,
            "raw": pipeline,
        }
    )


class GitLabProvider:
    """Fetch GitLab CI/CD pipelines for each configured project.

    Configured with ``PIPE_PING_GITLAB__TOKEN`` and ``PIPE_PING_GITLAB__PROJECTS``
    (a JSON list such as ``["group/project"]``).
    """

    settings: "GitLabSettings"
    session: aiohttp.ClientSession | None

    def __init__(self) -> None:
        self.settings = get_settings().gitlab
        self.session = None

    async def setup(self) -> None:
        if self.settings.token is None:
            raise PluginUnavailableError(
                "Set PIPE_PING_GITLAB__TOKEN to enable the GitLab provider"
            )
        if not self.settings.projects:
            raise PluginUnavailableError(
                "Set PIPE_PING_GITLAB__PROJECTS to a JSON list of projects to monitor"
            )

        self.session = aiohttp.ClientSession(
            headers={
                "PRIVATE-TOKEN": self.settings.token.get_secret_value(),
                "User-Agent": "pipe-ping",
            },
            timeout=aiohttp.ClientTimeout(total=30),
        )

    async def teardown(self) -> None:
        if self.session is not None:
            await self.session.close()

    async def poll(self) -> list[PipelineResult]:
        """Fetch recent pipelines for every project concurrently.

        If a project cannot be fetched, the error is logged and the other
        projects' results are still returned.
        """
        projects = self.settings.projects
        outcomes = await asyncio.gather(
            *(self.fetch_pipelines(project) for project in projects),
            return_exceptions=True,
        )

        results: list[PipelineResult] = []
        for project, outcome in zip(projects, outcomes, strict=True):
            if isinstance(outcome, BaseException):
                module_logger.error(
                    "Polling %s failed",
                    project,
                    exc_info=outcome,
                    extra={"repo": project},
                )
                continue
            results.extend(outcome)

        return results

    async def fetch_pipelines(self, project: str) -> list[PipelineResult]:
        if self.session is None:
            raise RuntimeError("GitLabProvider.setup() must be called before polling")

        url = f"{self.settings.api_url}/projects/{quote(project, safe='')}/pipelines"
        params = {"per_page": self.settings.pipelines_per_project}
        async with self.session.get(url, params=params) as response:
            response.raise_for_status()
            payload = await response.json()

        return [to_pipeline_result(project, pipeline) for pipeline in payload]

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class PipelineStatus(StrEnum):
    """The status of a pipeline run.

    Attributes:
        PENDING: Queued or waiting to start.
        RUNNING: In progress.
        SUCCESS: Finished successfully.
        FAILURE: Failed, including timeouts and startup failures.
        CANCELLED: Cancelled before finishing.
        SKIPPED: Skipped without running.
        UNKNOWN: A status that does not map to any of the values above.
    """

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"
    UNKNOWN = "unknown"


class PipelineResult(BaseModel):
    """The state of a single pipeline run, independent of provider.

    Together, ``provider`` and ``id`` identify a pipeline run. Repositories use
    them to detect status changes, so a provider must return the same ``id``
    for a pipeline run on every poll.

    Attributes:
        id: The pipeline run's ID, unique within its provider.
        provider: A short name for the provider, such as ``github``.
        repo: The repository the pipeline run belongs to, such as ``owner/repo``.
        branch: The branch the pipeline run was triggered on.
        commit_sha: The full SHA of the commit being built.
        status: The pipeline run's current status.
        url: A link to the pipeline run in the provider's web interface.
        created_at: When the pipeline run was created.
        started_at: When the pipeline run started, or ``None`` if it has not
            started.
        finished_at: When the pipeline run finished, or ``None`` if it has not
            finished.
        raw: The provider's original response for the pipeline run.
    """

    id: str
    provider: str
    repo: str
    branch: str
    commit_sha: str
    status: PipelineStatus
    url: str
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    raw: dict[str, Any]

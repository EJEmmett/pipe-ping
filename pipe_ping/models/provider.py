from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class PipelineStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"
    UNKNOWN = "unknown"


class PipelineResult(BaseModel):
    """Normalized snapshot of a single pipeline run.

    ``raw`` preserves the unmodified provider response so provider-specific
    fields are never discarded.
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

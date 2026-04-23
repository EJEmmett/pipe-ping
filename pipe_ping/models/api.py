from typing import TYPE_CHECKING

from pydantic import BaseModel, computed_field

if TYPE_CHECKING:
    from datetime import datetime

    from pipe_ping.models.common import PipelineStatus
    from pipe_ping.models.repository import PipelineResultDocument


class PipelineResultModel(BaseModel):
    id: str
    provider: str
    repo: str
    branch: str
    commit_sha: str
    status: "PipelineStatus"
    url: str
    created_at: "datetime"
    started_at: "datetime | None"
    finished_at: "datetime | None"

    @computed_field
    @property
    def duration_seconds(self) -> float | None:
        if self.started_at is None or self.finished_at is None:
            return None

        return (self.finished_at - self.started_at).total_seconds()

    @classmethod
    def from_document(cls, doc: "PipelineResultDocument") -> "PipelineResultModel":
        return cls(
            id=doc.id,
            provider=doc.provider,
            repo=doc.repo,
            branch=doc.branch,
            commit_sha=doc.commit_sha,
            status=doc.status,
            url=doc.url,
            created_at=doc.created_at,
            started_at=doc.started_at,
            finished_at=doc.finished_at,
        )


class BuildSummary(BaseModel):
    repo: str
    total_runs: int
    failure_rate: float
    last_status: "PipelineStatus"
    last_run_at: "datetime"

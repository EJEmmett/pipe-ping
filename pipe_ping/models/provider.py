from datetime import datetime

from pydantic import BaseModel

from pipe_ping.models.common import PipelineStatus


class PipelineResult(BaseModel):
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
    raw: dict

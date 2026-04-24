from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from pipe_ping.models.common import PipelineStatus

if TYPE_CHECKING:
    from pipe_ping.models.provider import PipelineResult


class PipelineResultDocument(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias="_id")

    @classmethod
    def from_result(cls, result: "PipelineResult") -> "PipelineResultDocument":
        return cls(
            _id=f"{result.repo}#{result.id}",
            **result.model_dump(exclude={"id"}),
        )

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

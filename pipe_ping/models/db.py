from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from datetime import datetime

    from pipe_ping.models.common import PipelineStatus


class PipelineResultDocument(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias="_id")
    provider: str
    repo: str
    branch: str
    commit_sha: str
    status: "PipelineStatus"
    url: str
    created_at: "datetime"
    started_at: "datetime | None"
    finished_at: "datetime | None"
    raw: dict

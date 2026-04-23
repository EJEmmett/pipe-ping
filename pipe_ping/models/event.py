from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from pipe_ping.models import PipelineResultDocument, PipelineStatus


class StatusChangeEvent(BaseModel):
    repo: str
    provider: str
    previous_status: "PipelineStatus | None"  # None on first poll
    current_status: "PipelineStatus"
    build: "PipelineResultDocument"

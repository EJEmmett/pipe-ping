from datetime import UTC, datetime

import pytest
from pipe_ping.models.common import PipelineStatus
from pipe_ping.models.provider import PipelineResult


@pytest.fixture
def pipeline_result() -> PipelineResult:
    return PipelineResult(
        id="42",
        provider="github",
        repo="owner/repo",
        branch="main",
        commit_sha="abc123",
        status=PipelineStatus.SUCCESS,
        url="https://github.com/owner/repo/actions/runs/42",
        created_at=datetime(2026, 4, 24, 12, 0, 0, tzinfo=UTC),
        started_at=datetime(2026, 4, 24, 12, 0, 5, tzinfo=UTC),
        finished_at=datetime(2026, 4, 24, 12, 1, 0, tzinfo=UTC),
        raw={"id": 42},
    )

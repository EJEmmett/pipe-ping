from datetime import UTC, datetime

import pytest
from pipe_ping.models.provider import PipelineResult, PipelineStatus
from pydantic import ValidationError


@pytest.fixture
def result_data():
    return {
        "id": "test-1",
        "provider": "test-provider",
        "repo": "org/repo",
        "branch": "main",
        "commit_sha": "abc123",
        "status": PipelineStatus.SUCCESS,
        "url": "https://ci.example.com/pipelines/1",
        "created_at": datetime(2000, 1, 1, tzinfo=UTC),
        "started_at": None,
        "finished_at": None,
        "raw": {},
    }


@pytest.mark.parametrize(
    ("value", "member"),
    [
        ("pending", PipelineStatus.PENDING),
        ("running", PipelineStatus.RUNNING),
        ("success", PipelineStatus.SUCCESS),
        ("failure", PipelineStatus.FAILURE),
        ("cancelled", PipelineStatus.CANCELLED),
        ("skipped", PipelineStatus.SKIPPED),
        ("unknown", PipelineStatus.UNKNOWN),
    ],
)
def test_pipeline_status_value(value, member):
    assert member.value == value


@pytest.mark.parametrize(
    ("value", "member"),
    [
        ("pending", PipelineStatus.PENDING),
        ("running", PipelineStatus.RUNNING),
        ("success", PipelineStatus.SUCCESS),
        ("failure", PipelineStatus.FAILURE),
        ("cancelled", PipelineStatus.CANCELLED),
        ("skipped", PipelineStatus.SKIPPED),
        ("unknown", PipelineStatus.UNKNOWN),
    ],
)
def test_pipeline_status_from_string(value, member):
    assert PipelineStatus(value) is member


def test_pipeline_result_valid(result_data):
    result = PipelineResult(**result_data)
    assert result.id == "test-1"
    assert result.status is PipelineStatus.SUCCESS


@pytest.mark.parametrize(
    "field",
    ["id", "provider", "repo", "branch", "commit_sha", "status", "url", "created_at"],
)
def test_pipeline_result_missing_required_field(result_data, field):
    data = dict(result_data)
    del data[field]
    with pytest.raises(ValidationError):
        PipelineResult(**data)


def test_pipeline_result_nullable_timestamps(result_data):
    result = PipelineResult(**result_data)
    assert result.started_at is None
    assert result.finished_at is None


def test_pipeline_result_with_timestamps(result_data):
    ts = datetime(2000, 6, 15, tzinfo=UTC)
    result_data["started_at"] = ts
    result_data["finished_at"] = ts
    result = PipelineResult(**result_data)
    assert result.started_at == ts
    assert result.finished_at == ts


def test_pipeline_result_invalid_status(result_data):
    result_data["status"] = "not-a-status"
    with pytest.raises(ValidationError):
        PipelineResult(**result_data)


def test_pipeline_result_raw_preserved(result_data):
    result_data["raw"] = {"key": "value", "nested": {"a": 1}}
    result = PipelineResult(**result_data)
    assert result.raw == {"key": "value", "nested": {"a": 1}}

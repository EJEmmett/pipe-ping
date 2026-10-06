import io
from datetime import UTC, datetime

import pytest
from pipe_ping.models.provider import PipelineResult, PipelineStatus
from pipe_ping.plugin._impl.console import ConsoleNotifier, format_result
from rich.console import Console


@pytest.fixture
def result():
    return PipelineResult(
        id="run-1",
        provider="github",
        repo="owner/repo",
        branch="main",
        commit_sha="acb5820ced9479c074f688cc328bf03f341a511d",
        status=PipelineStatus.FAILURE,
        url="https://github.com/owner/repo/actions/runs/1",
        created_at=datetime(2000, 1, 1, tzinfo=UTC),
        started_at=None,
        finished_at=None,
        raw={},
    )


@pytest.fixture
def notifier():
    notifier = ConsoleNotifier()
    notifier.console = Console(file=io.StringIO(), width=200, color_system=None)
    return notifier


def test_format_result_contains_fields(result):
    line = format_result(result).plain

    assert line == (
        "✗ failure    owner/repo  main  acb5820  "
        "https://github.com/owner/repo/actions/runs/1"
    )


@pytest.mark.parametrize("status", list(PipelineStatus))
def test_format_result_handles_every_status(result, status):
    result.status = status

    assert status.value in format_result(result).plain


def test_format_result_does_not_interpret_markup(result):
    result.branch = "fix/[bold]wip[/bold]"

    assert "fix/[bold]wip[/bold]" in format_result(result).plain


async def test_notify_prints_one_line_per_result(notifier, result):
    other = result.model_copy(update={"id": "run-2", "branch": "develop"})

    await notifier.notify([result, other])

    lines = notifier.console.file.getvalue().splitlines()
    assert len(lines) == 2
    assert "main" in lines[0]
    assert "develop" in lines[1]


async def test_notify_empty_prints_nothing(notifier):
    await notifier.notify([])

    assert notifier.console.file.getvalue() == ""

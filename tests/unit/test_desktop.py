from datetime import UTC, datetime
from unittest.mock import AsyncMock

import desktop_notifier
import pytest
from pipe_ping.models.provider import PipelineResult, PipelineStatus
from pipe_ping.plugin._impl.desktop import DesktopNotifier
from pipe_ping.plugin.errors import PluginUnavailableError


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
def toaster():
    toaster = AsyncMock(spec=desktop_notifier.DesktopNotifier)
    toaster.request_authorisation.return_value = True
    toaster.get_capabilities.return_value = frozenset()
    return toaster


@pytest.fixture
def notifier(toaster):
    notifier = DesktopNotifier()
    notifier.toaster = toaster
    return notifier


async def test_setup_succeeds_when_service_available(notifier):
    await notifier.setup()


async def test_setup_raises_when_not_authorised(notifier, toaster):
    toaster.request_authorisation.return_value = False

    with pytest.raises(PluginUnavailableError, match="not authorised"):
        await notifier.setup()


async def test_setup_raises_when_service_missing(notifier, toaster):
    toaster.get_capabilities.side_effect = RuntimeError("no dbus service")

    with pytest.raises(
        PluginUnavailableError, match="does not support desktop toasts"
    ) as exc_info:
        await notifier.setup()

    assert isinstance(exc_info.value.__cause__, RuntimeError)


@pytest.mark.parametrize(
    ("status", "urgency"),
    [
        (PipelineStatus.FAILURE, desktop_notifier.Urgency.Critical),
        (PipelineStatus.SUCCESS, desktop_notifier.Urgency.Normal),
        (PipelineStatus.CANCELLED, desktop_notifier.Urgency.Normal),
    ],
)
async def test_notify_sends_final_statuses(notifier, toaster, result, status, urgency):
    result.status = status

    await notifier.notify([result])

    toaster.send.assert_awaited_once()
    kwargs = toaster.send.await_args.kwargs
    assert kwargs["title"] == f"owner/repo: {status.value}"
    assert kwargs["message"] == "main @ acb5820"
    assert kwargs["urgency"] is urgency
    assert kwargs["thread"] == "owner/repo"


@pytest.mark.parametrize(
    "status",
    [
        PipelineStatus.PENDING,
        PipelineStatus.RUNNING,
        PipelineStatus.SKIPPED,
        PipelineStatus.UNKNOWN,
    ],
)
async def test_notify_skips_non_final_statuses(notifier, toaster, result, status):
    result.status = status

    await notifier.notify([result])

    toaster.send.assert_not_awaited()


async def test_notify_click_opens_each_run_url(notifier, toaster, result, monkeypatch):
    opened = []
    monkeypatch.setattr("webbrowser.open", opened.append)
    other = result.model_copy(update={"url": "https://github.com/owner/repo/runs/2"})

    await notifier.notify([result, other])
    for call in toaster.send.await_args_list:
        call.kwargs["on_clicked"]()

    assert opened == [result.url, other.url]

import asyncio
from datetime import UTC, datetime

import pytest
from pipe_ping.models.provider import PipelineResult, PipelineStatus
from pipe_ping.plugin.errors import PluginUnavailableError

pytestmark = pytest.mark.integration


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


async def test_setup_succeeds_with_notification_service(notifier, notification_server):
    await notifier.setup()


async def test_setup_raises_without_notification_service(notifier):
    with pytest.raises(PluginUnavailableError, match="does not support desktop toasts"):
        await notifier.setup()


@pytest.mark.parametrize(
    ("status", "urgency"),
    [
        (PipelineStatus.FAILURE, 2),
        (PipelineStatus.SUCCESS, 1),
        (PipelineStatus.CANCELLED, 1),
    ],
)
async def test_notify_sends_toast(
    notifier, notification_server, result, status, urgency
):
    result.status = status
    await notifier.setup()

    await notifier.notify([result])

    [toast] = notification_server.notifications
    assert toast["app_name"] == "Pipe-Ping"
    assert toast["summary"] == f"owner/repo: {status.value}"
    assert toast["body"] == "main @ acb5820"
    assert toast["hints"]["urgency"] == urgency


async def test_notify_skips_non_final_status(notifier, notification_server, result):
    result.status = PipelineStatus.RUNNING
    await notifier.setup()

    await notifier.notify([result])

    assert notification_server.notifications == []


async def test_click_opens_run_url(notifier, notification_server, result, opened_urls):
    await notifier.setup()
    await notifier.notify([result])
    [toast] = notification_server.notifications
    assert "default" in toast["actions"]

    notification_server.ActionInvoked(1, "default")

    assert await asyncio.wait_for(opened_urls.get(), timeout=2) == result.url

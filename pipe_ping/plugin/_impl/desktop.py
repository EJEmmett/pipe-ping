import webbrowser
from functools import partial
from typing import TYPE_CHECKING

import desktop_notifier
from desktop_notifier.backends.dummy import DummyNotificationCenter
from desktop_notifier.main import get_backend_class

from pipe_ping.models.provider import PipelineStatus
from pipe_ping.plugin.errors import PluginUnavailableError

if TYPE_CHECKING:
    from pipe_ping.models.provider import PipelineResult

_URGENCY: dict[PipelineStatus, desktop_notifier.Urgency] = {
    PipelineStatus.FAILURE: desktop_notifier.Urgency.Critical,
    PipelineStatus.SUCCESS: desktop_notifier.Urgency.Normal,
    PipelineStatus.CANCELLED: desktop_notifier.Urgency.Normal,
}


class DesktopNotifier:
    """Notify when a pipeline run succeeds, fails or is cancelled.

    Clicking the notification opens the pipeline run in the browser.
    """

    toaster: desktop_notifier.DesktopNotifier

    def __init__(self) -> None:
        self.toaster = desktop_notifier.DesktopNotifier(app_name="Pipe-Ping")

    async def setup(self) -> None:
        """Raise :class:`PluginUnavailableError` if notifications cannot be shown."""
        if get_backend_class() is DummyNotificationCenter:
            raise PluginUnavailableError(
                "Desktop notifications are not supported on this system. On macOS, "
                "Pipe-Ping must run from an app bundle"
            )

        if not await self.toaster.request_authorisation():
            raise PluginUnavailableError(
                "Desktop notifications are not allowed for Pipe-Ping. Enable them "
                "in your system settings"
            )

        try:
            await self.toaster.get_capabilities()
        except Exception as e:
            raise PluginUnavailableError(
                "Desktop notifications are unavailable because no notification "
                "service is running"
            ) from e

    async def teardown(self) -> None: ...

    async def notify(self, results: "list[PipelineResult]") -> None:
        for result in results:
            urgency = _URGENCY.get(result.status)
            if urgency is None:
                continue

            await self.toaster.send(
                title=f"{result.repo}: {result.status.value}",
                message=f"{result.branch} @ {result.commit_sha[:7]}",
                urgency=urgency,
                on_clicked=partial(webbrowser.open, result.url),
                thread=result.repo,
            )

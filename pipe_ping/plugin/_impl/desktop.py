import webbrowser
from functools import partial
from typing import TYPE_CHECKING

import desktop_notifier

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
    """Show a native toast for each run that reaches a final status.

    Pending and running transitions are skipped so a single run produces one
    toast rather than three. Clicking a toast opens the run in the browser.
    """

    toaster: desktop_notifier.DesktopNotifier

    def __init__(self) -> None:
        self.toaster = desktop_notifier.DesktopNotifier(app_name="Pipe-Ping")

    async def setup(self) -> None:
        """Fail fast when toasts cannot be shown."""
        if not await self.toaster.request_authorisation():
            raise PluginUnavailableError(
                "Desktop toasts are not authorised; allow notifications for "
                "Pipe-Ping in your system settings"
            )

        try:
            await self.toaster.get_capabilities()
        except Exception as e:
            raise PluginUnavailableError(
                "This environment does not support desktop toasts "
                "(no notification service found)"
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

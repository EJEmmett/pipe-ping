from typing import TYPE_CHECKING

from rich.console import Console
from rich.text import Text

from pipe_ping.models.provider import PipelineStatus

if TYPE_CHECKING:
    from pipe_ping.models.provider import PipelineResult

_STATUS_STYLES: dict[PipelineStatus, tuple[str, str]] = {
    PipelineStatus.PENDING: ("…", "dim"),
    PipelineStatus.RUNNING: ("▶", "blue"),
    PipelineStatus.SUCCESS: ("✓", "green"),
    PipelineStatus.FAILURE: ("✗", "bold red"),
    PipelineStatus.CANCELLED: ("⊘", "yellow"),
    PipelineStatus.SKIPPED: ("↷", "dim"),
    PipelineStatus.UNKNOWN: ("?", "magenta"),
}


def format_result(result: "PipelineResult") -> Text:
    """Format *result* as a single console line.

    The line is built from ``Text`` parts rather than markup so that names
    containing ``[`` are not parsed as rich styles.
    """
    icon, style = _STATUS_STYLES[result.status]

    return Text.assemble(
        (f"{icon} {result.status.value:<9}", style),
        "  ",
        (result.repo, "bold"),
        "  ",
        result.branch,
        "  ",
        (result.commit_sha[:7], "dim"),
        "  ",
        (result.url, f"link {result.url}"),
    )


class ConsoleNotifier:
    console: Console

    def __init__(self) -> None:
        self.console = Console(soft_wrap=True)

    async def setup(self) -> None: ...
    async def teardown(self) -> None: ...

    async def notify(self, results: "list[PipelineResult]") -> None:
        for result in results:
            self.console.print(format_result(result))

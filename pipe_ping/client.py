import asyncio
import logging
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from pipe_ping.daemon import start_pipe_ping
from pipe_ping.plugin import (
    NOTIFIER_GROUP,
    PROVIDER_GROUP,
    REPOSITORY_GROUP,
    discover_entry_points,
)
from pipe_ping.plugin.errors import PipePingPluginError
from pipe_ping.tools import get_settings, initialize_logging

app = typer.Typer(no_args_is_help=True)
list_app = typer.Typer(help="List registered plugins.")
app.add_typer(list_app, name="list")

module_logger = logging.getLogger(__name__)
VerboseOption = Annotated[
    int,
    typer.Option(
        "--verbose",
        "-v",
        count=True,
        help="Increase verbosity (-v for INFO, -vv for DEBUG).",
    ),
]


def initialize_verbosity(
    verbose: int,
) -> None:
    levels = {0: logging.WARNING, 1: logging.INFO, 2: logging.DEBUG}
    settings = get_settings()
    initialize_logging(settings, levels.get(verbose, logging.DEBUG))


def table_group_entrypoints(group: str) -> None:
    table = Table("Name", "Location", show_header=True)

    for ep in discover_entry_points(group=group):
        table.add_row(ep.name, ep.value)

    if table.row_count == 0:
        typer.echo("(none)")
        return

    Console().print(table)


@app.command()
def daemon(verbose: VerboseOption = 0) -> None:
    """Run the pipe-ping daemon."""
    initialize_verbosity(verbose)

    try:
        asyncio.run(start_pipe_ping())
    except PipePingPluginError as e:
        typer.echo(f"pipe-ping: {e}", err=True)
        raise typer.Exit(code=1) from e


@list_app.command("providers")
def list_providers(verbose: VerboseOption = 0) -> None:
    """List registered provider plugins."""
    initialize_verbosity(verbose)

    table_group_entrypoints(PROVIDER_GROUP)


@list_app.command("repository")
def list_repository(verbose: VerboseOption = 0) -> None:
    """List registered repository plugins."""
    initialize_verbosity(verbose)

    table_group_entrypoints(REPOSITORY_GROUP)


@list_app.command("notifiers")
def list_notifiers(verbose: VerboseOption = 0) -> None:
    """List registered notifier plugins."""
    initialize_verbosity(verbose)

    table_group_entrypoints(NOTIFIER_GROUP)

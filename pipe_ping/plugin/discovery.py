import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from importlib.metadata import EntryPoint, EntryPoints, entry_points
from typing import TYPE_CHECKING, Protocol, cast, overload

from pipe_ping.plugin.errors import (
    AllPluginsFailedError,
    NoPluginsConfiguredError,
    PluginIsUniqueError,
    PluginUnavailableError,
)
from pipe_ping.utils.asyncio import ensure_async_call

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from contextlib import AbstractAsyncContextManager
    from typing import Literal

module_logger = logging.getLogger(__name__)


class Plugin(Protocol):
    """Optional lifecycle methods for plugins.

    ``setup`` and ``teardown`` are called only when defined, so plugins may
    omit them.
    """

    async def setup(self) -> None:
        """Prepare the plugin.

        Called once at startup, with a 10-second timeout. Raise
        ``PluginUnavailableError`` if the plugin cannot run.
        """
        ...

    async def teardown(self) -> None:
        """Release the plugin's resources.

        Called once at shutdown, with a 10-second timeout.
        """
        ...


@dataclass
class PluginInfo[T: Plugin]:
    """A loaded plugin and the entry point it was loaded from."""

    entrypoint: EntryPoint
    plugin: T


def discover_entry_points(group: str) -> EntryPoints:
    module_logger.debug("Discovering plugin group %s", group)

    known_entry_points = entry_points(group=group)

    module_logger.debug(
        "Discovered %d plugin(s) in group %s",
        len(known_entry_points),
        group,
        extra={"entry_points": [ep.name for ep in known_entry_points]},
    )

    return known_entry_points


def is_builtin(entry_point: EntryPoint) -> bool:
    return entry_point.module.partition(".")[0] == "pipe_ping"


def select_unique_entry_point(entry_points: EntryPoints, group: str) -> EntryPoint:
    """Select the single plugin allowed in *group*.

    A third-party plugin takes precedence over the built-in one. If more than
    one candidate remains, the error lists all of them.
    """
    candidates = list(entry_points)
    custom = [ep for ep in candidates if not is_builtin(ep)]
    if custom:
        candidates = custom

    if len(candidates) > 1:
        names = ", ".join(f"{ep.name} ({ep.value})" for ep in candidates)
        raise PluginIsUniqueError(
            f"{group} allows one plugin but {len(candidates)} are installed: {names}. "
            "Uninstall all but one."
        )

    [selected] = candidates
    if custom:
        module_logger.info(
            "Using %s instead of the built-in %s plugin", selected.name, group
        )
    return selected


@asynccontextmanager
async def _discover_plugins[T: Plugin](
    group: str, unique: bool = False
) -> "AsyncIterator[list[PluginInfo[T]] | PluginInfo[T]]":
    plugin_infos: list[PluginInfo[T]] = []

    known_entry_points = discover_entry_points(group)
    if not known_entry_points:
        raise NoPluginsConfiguredError(f"No plugins are installed in {group}")

    if unique:
        selected_entry_points = [select_unique_entry_point(known_entry_points, group)]
    else:
        selected_entry_points = list(known_entry_points)

    for ep in selected_entry_points:
        try:
            plugin_cls = cast("type[T]", ep.load())
        except Exception:
            module_logger.exception("Failed to load plugin %s", ep.name)
            continue

        try:
            plugin_instance: T = plugin_cls()
        except Exception:
            module_logger.exception("Failed to create plugin %s", ep.name)
            continue

        if hasattr(plugin_instance, "setup"):
            try:
                await asyncio.wait_for(ensure_async_call(plugin_instance.setup), 10)
            except PluginUnavailableError as e:
                module_logger.warning("Skipping plugin %s: %s", ep.name, e)
                continue
            except Exception:
                module_logger.exception("Failed to set up plugin %s", ep.name)
                continue

        module_logger.debug("Loaded plugin %s", ep.name)
        plugin_infos.append(PluginInfo(ep, plugin_instance))

    if not plugin_infos:
        raise AllPluginsFailedError(f"No plugins in {group} could be loaded")

    if unique:
        yield plugin_infos[0]
    else:
        yield plugin_infos

    for plugin_info in plugin_infos:
        if hasattr(plugin_info.plugin, "teardown"):
            try:
                await asyncio.wait_for(
                    ensure_async_call(plugin_info.plugin.teardown), 10
                )
            except Exception:
                module_logger.exception(
                    "Failed to tear down plugin %s", plugin_info.entrypoint.name
                )
                continue


@overload
def discover_plugins[T: Plugin](
    group: str, unique: "Literal[True]"
) -> "AbstractAsyncContextManager[PluginInfo[T]]": ...


@overload
def discover_plugins[T: Plugin](
    group: str, unique: bool = ...
) -> "AbstractAsyncContextManager[list[PluginInfo[T]]]": ...


def discover_plugins[T: Plugin](
    group: str, unique: bool = False
) -> "AbstractAsyncContextManager[list[PluginInfo[T]] | PluginInfo[T]]":
    """Load and set up the plugins in *group*, and tear them down on exit.

    A plugin that fails to load or set up is logged and skipped. With *unique*,
    a single plugin is returned instead of a list.
    """
    return _discover_plugins(group, unique)

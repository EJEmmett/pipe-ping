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
    """Optional lifecycle protocol for plugins.

    The loader calls ``setup`` and ``teardown`` only when present, so plugins
    that need no lifecycle management can omit them entirely.
    """

    async def setup(self) -> None: ...
    async def teardown(self) -> None: ...


@dataclass
class PluginInfo[T: Plugin]:
    """A loaded plugin paired with its entry-point metadata.

    The entry-point is retained alongside the instance so that the plugin's
    registered name is available for logging without requiring a ``name``
    attribute on the protocol.
    """

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


@asynccontextmanager
async def _discover_plugins[T: Plugin](
    group: str, unique: bool = False
) -> "AsyncIterator[list[PluginInfo[T]] | PluginInfo[T]]":
    plugin_infos: list[PluginInfo[T]] = []

    known_entry_points = discover_entry_points(group)
    if not known_entry_points:
        raise NoPluginsConfiguredError(f"{group} contains no plugins")

    if unique and len(known_entry_points) > 1:
        raise PluginIsUniqueError(f"{group} contains more than one plugin")

    for ep in known_entry_points:
        try:
            plugin_cls = cast("type[T]", ep.load())
        except Exception:
            module_logger.exception("Plugin %s discovery failed", ep.name)
            continue

        try:
            plugin_instance: T = plugin_cls()
        except Exception:
            module_logger.exception("Plugin %s initialization failed", ep.name)
            continue

        if hasattr(plugin_instance, "setup"):
            try:
                await asyncio.wait_for(ensure_async_call(plugin_instance.setup), 10)
            except PluginUnavailableError as e:
                module_logger.warning("Plugin %s unavailable: %s", ep.name, e)
                continue
            except Exception:
                module_logger.exception("Plugin %s setup failed", ep.name)
                continue

        module_logger.debug("Loaded plugin %s", ep.name)
        plugin_infos.append(PluginInfo(ep, plugin_instance))

    if not plugin_infos:
        raise AllPluginsFailedError(f"Every plugin in {group} failed to load")

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
                    "Plugin %s teardown failed", plugin_info.entrypoint.name
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
    """Async context manager that loads, sets up, and yields plugins in *group*.

    Individual plugin failures are skipped rather than aborting the group.
    Teardown runs for every successfully set-up plugin on context-manager exit.
    """
    return _discover_plugins(group, unique)

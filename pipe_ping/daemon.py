import asyncio
import logging
import signal
import sys
from asyncio.taskgroups import TaskGroup
from contextlib import AsyncExitStack
from typing import TYPE_CHECKING

from pipe_ping.plugin import (
    NOTIFIER_GROUP,
    PROVIDER_GROUP,
    REPOSITORY_GROUP,
    PluginInfo,
    discover_plugins,
)
from pipe_ping.utils.asyncio import ensure_async_call

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import FrameType

    from pipe_ping.plugin.notifier import NotifierPlugin
    from pipe_ping.plugin.provider import ProviderPlugin
    from pipe_ping.plugin.repository import RepositoryPlugin

module_logger = logging.getLogger(__name__)


async def poll_once(
    provider: "PluginInfo[ProviderPlugin]",
    repository: "PluginInfo[RepositoryPlugin]",
    notifiers: "list[PluginInfo[NotifierPlugin]]",
    timeout: float = 60.0,
    logger: logging.Logger | None = None,
) -> None:
    """Poll *provider* once, save the results and send any changes to *notifiers*."""
    if logger is None:
        logger = module_logger

    provider_name = provider.entrypoint.name
    repository_name = repository.entrypoint.name

    provider_extra = {
        "provider": provider_name,
    }
    repository_extra = provider_extra | {
        "repository": repository_name,
    }

    logger.debug("Polling %s", provider_name, extra=provider_extra)
    try:
        results = await asyncio.wait_for(
            ensure_async_call(provider.plugin.poll), timeout
        )
    except TimeoutError:
        logger.warning(
            "Poll timed out after %.1fs",
            timeout,
            extra={"provider": provider_name, "timeout": timeout},
        )
        return

    except Exception:
        logger.exception("Poll failed", extra=provider_extra)
        return

    logger.debug(
        "Polled %d result(s)",
        len(results),
        extra=provider_extra | {"result_count": len(results)},
    )

    logger.debug(
        "Saving %d result(s) to %s",
        len(results),
        repository_name,
        extra=repository_extra
        | {
            "result_count": len(results),
        },
    )
    try:
        changes = await asyncio.wait_for(
            ensure_async_call(repository.plugin.save, results), timeout
        )
    except TimeoutError:
        logger.warning(
            "Save to %s timed out after %.1fs",
            repository_name,
            timeout,
            extra=repository_extra
            | {
                "timeout": timeout,
            },
        )
        return
    except Exception:
        logger.exception(
            "Save to %s failed",
            repository_name,
            extra=repository_extra,
        )
        return

    if not changes:
        logger.debug("No changes to notify", extra=provider_extra)
        return

    notifier_names = [n.entrypoint.name for n in notifiers]
    logger.debug(
        "Sending %d change(s) to %d notifier(s)",
        len(changes),
        len(notifiers),
        extra=provider_extra
        | {"notifiers": notifier_names, "change_count": len(changes)},
    )
    for notifier in notifiers:
        notifier_name = notifier.entrypoint.name
        notifier_extra = {"notifier": notifier_name}

        logger.debug("Notifying %s", notifier_name, extra=notifier_extra)
        try:
            await asyncio.wait_for(
                ensure_async_call(notifier.plugin.notify, changes), timeout
            )
        except TimeoutError:
            logger.warning(
                "Notifier %s timed out after %.1fs",
                notifier_name,
                timeout,
                extra=notifier_extra | {"timeout": timeout},
            )
        except Exception:
            logger.exception(
                "Notifier %s failed",
                notifier_name,
                extra=notifier_extra,
            )


async def schedule_provider(
    provider: "PluginInfo[ProviderPlugin]",
    repository: "PluginInfo[RepositoryPlugin]",
    notifiers: "list[PluginInfo[NotifierPlugin]]",
    poll_interval: float = 60.0,
    timeout: float = 60.0,
    logger: logging.Logger | None = None,
) -> None:
    """Call :func:`poll_once` in a loop, sleeping *poll_interval* seconds after each."""
    while True:
        await poll_once(provider, repository, notifiers, timeout, logger)
        await asyncio.sleep(poll_interval)


def get_shutdown_handler(
    stop_event: asyncio.Event, loop: asyncio.AbstractEventLoop
) -> "Callable[[int, FrameType | None], None]":
    """Return a signal handler that sets *stop_event*.

    The event is set through ``call_soon_threadsafe`` so that the event loop
    wakes up even while it is waiting on I/O.
    """

    def _wrapped(signum: int, frame: "FrameType | None") -> None:
        loop.call_soon_threadsafe(stop_event.set)

    return _wrapped


async def start_pipe_ping() -> None:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    handler = get_shutdown_handler(stop_event, loop)

    signal.signal(signal.SIGINT, handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handler)
    if sys.platform == "win32" and hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, handler)

    async with AsyncExitStack() as stack:
        providers: list[PluginInfo[ProviderPlugin]] = await stack.enter_async_context(
            discover_plugins(PROVIDER_GROUP)
        )
        module_logger.info(
            "Loaded %d provider(s)",
            len(providers),
            extra={"providers": [provider.entrypoint.name for provider in providers]},
        )
        repository: PluginInfo[RepositoryPlugin] = await stack.enter_async_context(
            discover_plugins(REPOSITORY_GROUP, unique=True)
        )
        module_logger.info(
            "Loaded repository %s",
            repository.entrypoint.name,
            extra={"repository": repository.entrypoint.name},
        )
        notifiers: list[PluginInfo[NotifierPlugin]] = await stack.enter_async_context(
            discover_plugins(NOTIFIER_GROUP)
        )
        module_logger.info(
            "Loaded %d notifier(s)",
            len(notifiers),
            extra={"notifiers": [notifier.entrypoint.name for notifier in notifiers]},
        )

        tg = await stack.enter_async_context(TaskGroup())
        module_logger.info("Polling %d provider(s)", len(providers))
        tasks = [
            tg.create_task(schedule_provider(provider, repository, notifiers))
            for provider in providers
        ]

        await stop_event.wait()

        module_logger.info("Shutting down")
        for t in tasks:
            t.cancel()

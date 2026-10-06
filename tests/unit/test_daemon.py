import asyncio
import signal

from pipe_ping.daemon import get_shutdown_handler, poll_once
from pipe_ping.models.provider import PipelineStatus


async def test_get_shutdown_handler_returns_callable():
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    handler = get_shutdown_handler(stop_event, loop)
    assert callable(handler)


async def test_get_shutdown_handler_sets_stop_event():
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    handler = get_shutdown_handler(stop_event, loop)

    assert not stop_event.is_set()
    handler(signal.SIGINT, None)
    await asyncio.sleep(0)
    assert stop_event.is_set()


async def test_get_shutdown_handler_is_idempotent():
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    handler = get_shutdown_handler(stop_event, loop)

    handler(signal.SIGINT, None)
    handler(signal.SIGINT, None)
    await asyncio.sleep(0)
    assert stop_event.is_set()


async def test_poll_once_first_poll_notifies_nothing(
    phony_provider, memory_repository, phony_notifier
):
    await poll_once(phony_provider, memory_repository, [phony_notifier])

    assert phony_notifier.plugin.notified == []


async def test_poll_once_notifies_only_changes(
    phony_provider, memory_repository, phony_notifier
):
    await poll_once(phony_provider, memory_repository, [phony_notifier])
    running = phony_provider.plugin.results[2]
    finished = running.model_copy(update={"status": PipelineStatus.SUCCESS})
    phony_provider.plugin.results[2] = finished

    await poll_once(phony_provider, memory_repository, [phony_notifier])

    assert phony_notifier.plugin.notified == [finished]

import asyncio
import shutil
import subprocess
import sys
from importlib.metadata import EntryPoint

import pytest
from dbus_fast.aio import MessageBus
from pipe_ping.plugin import PROVIDER_GROUP, REPOSITORY_GROUP, PluginInfo
from pipe_ping.plugin._impl.desktop import DesktopNotifier
from pipe_ping.plugin._impl.github import GitHubProvider
from pipe_ping.tools import get_settings

from tests.fakes import NullRepository
from tests.integration.notification_server import (
    BUS_NAME,
    OBJECT_PATH,
    FakeNotificationServer,
)

BUS_CONFIG = """\
<!DOCTYPE busconfig PUBLIC "-//freedesktop//DTD D-Bus Bus Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">
<busconfig>
  <type>session</type>
  <listen>unix:tmpdir={tmpdir}</listen>
  <policy context="default">
    <allow send_destination="*" eavesdrop="true"/>
    <allow eavesdrop="true"/>
    <allow own="*"/>
  </policy>
</busconfig>
"""


@pytest.fixture
def dbus_session(tmp_path, monkeypatch):
    """Start a private session bus and point ``DBUS_SESSION_BUS_ADDRESS`` at it.

    The config has no ``<servicedir>``, so the host's real notification daemon
    can never be auto-activated onto this bus.
    """
    dbus_daemon = shutil.which("dbus-daemon")
    if sys.platform != "linux" or dbus_daemon is None:
        pytest.skip("dbus-daemon is required for desktop notification tests")

    config = tmp_path / "session.conf"
    config.write_text(BUS_CONFIG.format(tmpdir=tmp_path))

    with subprocess.Popen(  # noqa: S603
        [dbus_daemon, f"--config-file={config}", "--nofork", "--print-address"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as process:
        assert process.stdout is not None
        address = process.stdout.readline().strip()
        if not address:
            process.kill()
            _, stderr = process.communicate(timeout=5)
            pytest.skip(f"dbus-daemon failed to start: {stderr.strip()}")

        monkeypatch.setenv("DBUS_SESSION_BUS_ADDRESS", address)

        yield address

        process.terminate()


@pytest.fixture
async def notification_server(dbus_session):
    """Export a ``FakeNotificationServer`` on the private bus."""
    bus = await MessageBus().connect()
    server = FakeNotificationServer()
    bus.export(OBJECT_PATH, server)
    await bus.request_name(BUS_NAME)

    yield server

    bus.disconnect()
    await bus.wait_for_disconnect()


@pytest.fixture
def notifier(dbus_session):
    return DesktopNotifier()


@pytest.fixture
def opened_urls(monkeypatch):
    """Capture ``webbrowser.open`` calls; await ``get()`` to wait for a click."""
    urls: asyncio.Queue[str] = asyncio.Queue()
    monkeypatch.setattr("webbrowser.open", urls.put_nowait)
    return urls


@pytest.fixture
def github_settings(monkeypatch, github_api):
    """Configure the GitHub provider through the environment, as a user would."""
    monkeypatch.setenv("PIPE_PING_GITHUB__TOKEN", "test-token")
    monkeypatch.setenv("PIPE_PING_GITHUB__REPOS", '["owner/repo"]')
    monkeypatch.setenv("PIPE_PING_GITHUB__API_URL", github_api.url)
    get_settings.cache_clear()

    yield get_settings().github

    get_settings.cache_clear()


@pytest.fixture
async def github_provider(github_settings):
    """A set-up ``GitHubProvider`` wrapped as the daemon receives it."""
    provider = GitHubProvider()
    await provider.setup()

    yield PluginInfo(
        EntryPoint(
            name="GitHubProvider",
            value="pipe_ping.plugin._impl.github:GitHubProvider",
            group=PROVIDER_GROUP,
        ),
        provider,
    )

    await provider.teardown()


@pytest.fixture
def null_repository():
    return PluginInfo(
        EntryPoint(
            name="NullRepository",
            value="tests.fakes:NullRepository",
            group=REPOSITORY_GROUP,
        ),
        NullRepository(),
    )

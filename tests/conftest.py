import pytest
from aiohttp.test_utils import TestServer

from tests.github_server import FakeGitHubServer
from tests.gitlab_server import FakeGitLabServer


@pytest.fixture
async def github_api():
    """Run a ``FakeGitHubServer`` on localhost; its base URL is ``github_api.url``."""
    fake = FakeGitHubServer()
    async with TestServer(fake.app) as server:
        fake.url = str(server.make_url(""))
        yield fake


@pytest.fixture
async def gitlab_api():
    """Run a ``FakeGitLabServer`` on localhost; its base URL is ``gitlab_api.url``."""
    fake = FakeGitLabServer()
    async with TestServer(fake.app) as server:
        fake.url = str(server.make_url(""))
        yield fake

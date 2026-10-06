import pytest
from aiohttp.test_utils import TestServer

from tests.github_server import FakeGitHubServer


@pytest.fixture
async def github_api():
    """Run a ``FakeGitHubServer`` on localhost; its base URL is ``github_api.url``."""
    fake = FakeGitHubServer()
    async with TestServer(fake.app) as server:
        fake.url = str(server.make_url(""))
        yield fake

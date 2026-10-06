"""A fake GitHub REST API for tests, served over real HTTP by aiohttp.

Only the workflow-runs endpoint the GitHub provider calls is implemented.
Tests add runs per repository to ``runs``; any repository without an entry
responds with 404, like a missing or inaccessible repository on GitHub.
"""

from dataclasses import dataclass
from typing import Any

from aiohttp import web


@dataclass
class ReceivedRequest:
    path: str
    query: dict[str, str]
    headers: dict[str, str]


class FakeGitHubServer:
    def __init__(self) -> None:
        self.runs: dict[str, list[dict[str, Any]]] = {}
        self.requests: list[ReceivedRequest] = []
        # Base URL, set by the fixture once the server is listening.
        self.url = ""
        self.app = web.Application()
        self.app.router.add_get(
            "/repos/{owner}/{repo}/actions/runs", self.list_workflow_runs
        )

    async def list_workflow_runs(self, request: web.Request) -> web.Response:
        self.requests.append(
            ReceivedRequest(
                path=request.path,
                query=dict(request.query),
                headers=dict(request.headers),
            )
        )

        repo = f"{request.match_info['owner']}/{request.match_info['repo']}"
        if repo not in self.runs:
            raise web.HTTPNotFound

        runs = self.runs[repo]
        return web.json_response({"total_count": len(runs), "workflow_runs": runs})

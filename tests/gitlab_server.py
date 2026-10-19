from typing import Any

from aiohttp import web

from tests.github_server import ReceivedRequest


class FakeGitLabServer:
    def __init__(self) -> None:
        self.pipelines: dict[str, list[dict[str, Any]]] = {}
        self.requests: list[ReceivedRequest] = []
        self.url = ""
        self.app = web.Application()
        self.app.router.add_get("/projects/{project}/pipelines", self.list_pipelines)

    async def list_pipelines(self, request: web.Request) -> web.Response:
        self.requests.append(
            ReceivedRequest(
                path=request.raw_path.partition("?")[0],
                query=dict(request.query),
                headers=dict(request.headers),
            )
        )

        project = request.match_info["project"]
        if project not in self.pipelines:
            raise web.HTTPNotFound

        return web.json_response(self.pipelines[project])

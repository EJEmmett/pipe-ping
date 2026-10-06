import logging

import pytest
from pipe_ping.daemon import poll_once
from pipe_ping.plugin import NOTIFIER_GROUP, discover_entry_points, discover_plugins

pytestmark = pytest.mark.integration


@pytest.fixture
def workflow_run():
    return {
        "id": 30433642,
        "name": "CI",
        "head_branch": "main",
        "head_sha": "acb5820ced9479c074f688cc328bf03f341a511d",
        "status": "completed",
        "conclusion": "failure",
        "html_url": "https://github.com/owner/repo/actions/runs/30433642",
        "created_at": "2026-10-06T12:00:00Z",
        "updated_at": "2026-10-06T12:05:00Z",
        "run_started_at": "2026-10-06T12:00:05Z",
    }


async def test_github_failure_reaches_every_notifier(
    github_provider,
    github_api,
    null_repository,
    notification_server,
    workflow_run,
    capsys,
    caplog,
):
    github_api.runs["owner/repo"] = [workflow_run]
    registered = {ep.name for ep in discover_entry_points(NOTIFIER_GROUP)}

    async with discover_plugins(NOTIFIER_GROUP) as notifiers:
        loaded = {notifier.entrypoint.name for notifier in notifiers}
        assert loaded == registered, "every registered notifier must load"

        await poll_once(github_provider, null_repository, notifiers)

    assert [r for r in caplog.records if r.levelno >= logging.ERROR] == []

    console_output = capsys.readouterr().out
    assert "✗ failure" in console_output
    assert "owner/repo" in console_output

    [toast] = notification_server.notifications
    assert toast["summary"] == "owner/repo: failure"
    assert toast["body"] == "main @ acb5820"

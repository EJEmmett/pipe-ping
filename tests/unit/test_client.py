from pipe_ping.client import app
from typer.testing import CliRunner


def test_daemon_reports_plugin_failure_without_traceback(daemon_without_providers):
    result = CliRunner().invoke(app, ["daemon"])

    assert result.exit_code == 1
    assert "pipe-ping: no providers could be loaded" in result.output
    assert "Traceback" not in result.output

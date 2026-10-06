# Writing a plugin

Pipe-Ping is built from three kinds of plugin:

- **Providers** fetch pipeline runs from a CI/CD service.
- A **repository** stores pipeline runs and decides which status changes to
  report.
- **Notifiers** report those changes to the user.

A plugin is a class in an installed Python package, registered under an entry
point group. For a complete package, see the
[example plugin](https://github.com/EJEmmett/pipe-ping/tree/main/examples/plugin).

## 1. Implement the plugin

Each plugin class must implement the method for its kind:

| Entry point group | Required method |
| --- | --- |
| `pipe-ping.providers` | `async def poll(self) -> list[PipelineResult]` |
| `pipe-ping.repository` | `async def save(self, results: list[PipelineResult]) -> list[PipelineResult]` |
| `pipe-ping.notifiers` | `async def notify(self, results: list[PipelineResult]) -> None` |

The fields of `PipelineResult` are described in the
[API reference](../reference/api.md#pipe_ping.models.provider.PipelineResult).

For example, a provider for a hypothetical CI/CD service:

```python
from pipe_ping.models.provider import PipelineResult, PipelineStatus


class ExampleProvider:
    async def poll(self) -> list[PipelineResult]:
        return [
            PipelineResult(
                id="1234",
                provider="example",
                repo="owner/repo",
                branch="main",
                commit_sha="3f2a9c1e8b7d6f5a4c3b2a1908f7e6d5c4b3a291",
                status=PipelineStatus.SUCCESS,
                url="https://ci.example.com/owner/repo/runs/1234",
                created_at="2026-10-06T12:00:00Z",
                started_at="2026-10-06T12:00:05Z",
                finished_at="2026-10-06T12:04:30Z",
                raw={},
            )
        ]
```

- Datetime fields accept `datetime` objects or ISO 8601 strings.
- Pipe-Ping creates each plugin with no arguments. Read settings from
  environment variables or your own config file.

## 2. Add setup and teardown (optional)

`setup()` and `teardown()` run once at startup and shutdown. Use them to open
and close connections.

If the plugin cannot run, for example because it is not configured, raise
`PluginUnavailableError` from `setup()`. Pipe-Ping logs your message as a
warning and continues without the plugin:

```python
import os

from pipe_ping.plugin.errors import PluginUnavailableError


class ExampleProvider:
    async def setup(self) -> None:
        if not os.environ.get("EXAMPLE_TOKEN"):
            raise PluginUnavailableError("Set EXAMPLE_TOKEN to enable ExampleProvider")
```

## 3. Register the plugin

Register each class under its entry point group in your package's
`pyproject.toml`:

```toml
[project.entry-points."pipe-ping.providers"]
ExampleProvider = "pipe_ping_example:ExampleProvider"

[project.entry-points."pipe-ping.notifiers"]
ExampleNotifier = "pipe_ping_example:ExampleNotifier"
```

The entry point name, such as `ExampleProvider`, is shown by `pipe-ping list`
and in log messages.

!!! note "Repository plugins"

    Only one repository can be active. A third-party repository replaces the
    built-in SQLite repository. If more than one third-party repository is
    installed, Pipe-Ping lists them and exits.

## 4. Install and test the plugin

Install the plugin into the same environment as Pipe-Ping, then check that it
is registered:

```bash
uv tool install pipe-ping --with ./path/to/your-plugin
pipe-ping list providers
```

Run Pipe-Ping with `-v` to see which plugins load and any errors they raise:

```bash
pipe-ping daemon -v
```

## Next steps

See [How plugins run](runtime.md) for call order, timeouts and error handling.

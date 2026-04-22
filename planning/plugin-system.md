# Plugin System

All three extensible subsystems — providers, repositories, and notifiers — use the same
discovery mechanism. Adding a new plugin requires one file and one entry point registration.
No changes to the pipe-ping source are needed.

## Extras Model

All plugin code ships inside the `pipe_ping` package. What changes between installs is
which dependencies are present. Each optional dependency group unlocks one plugin:

```bash
pip install pipe-ping                              # core only — in-memory repository
pip install pipe-ping[github]                     # + GitHub Actions provider
pip install pipe-ping[gitlab]                     # + GitLab CI provider
pip install pipe-ping[mongodb]                    # + MongoDB repository
pip install pipe-ping[sqlite]                     # + SQLite repository
pip install pipe-ping[desktop]                    # + desktop toast notifier
pip install pipe-ping[webhook]                    # + webhook notifier
pip install pipe-ping[email]                      # + email notifier
pip install pipe-ping[sms]                        # + SMS notifier
pip install pipe-ping[github,mongodb,desktop]     # typical production setup
```

All entry points are declared unconditionally in `pyproject.toml`. When a plugin's
dependencies are not installed its module raises `ImportError` on import. The discovery
function catches this per plugin and logs a warning, so the remaining plugins continue
loading normally. The `memory` repository is the only plugin that requires no extra.

## Discovery Mechanism

Plugins are discovered at startup via `importlib.metadata.entry_points`. After loading
the class, core immediately calls `.create()` to get a configured instance:

```python
from importlib.metadata import entry_points

providers = {
    ep.name: ep.load().create()
    for ep in entry_points(group="pipe_ping.providers")
}
```

Each entry point maps a short name (e.g. `"github"`) to a class. `ep.load()` imports
the module and returns the class; `.create()` calls the plugin's factory to produce an
instance that has already read its own configuration from the environment. The result is
a dict of ready-to-use instances used throughout the scheduler.

Plugins self-register via `[project.entry-points.*]` in their `pyproject.toml`. Built-in
plugins live in this package and register themselves here. Third-party plugins ship their
own package and use the same mechanism — no changes to pipe-ping needed.

## Plugin-Owned Configuration

Core has no knowledge of any plugin's settings. Each plugin defines a private
pydantic-settings class with its own env prefix and reads from the environment inside
`create()`. Core only calls `create()` — it never inspects settings or passes
configuration to a plugin.

```python
class GitHubSettings(BaseSettings):
    token: str

    model_config = SettingsConfigDict(
        env_prefix="PIPE_PING_GITHUB_",
        env_file=".env",
    )

class GitHubProvider(BaseProvider):
    @classmethod
    def create(cls) -> "GitHubProvider":
        settings = GitHubSettings()
        return cls(token=settings.token)
```

Each plugin documents its own env vars. See [providers.md](providers.md),
[notifiers.md](notifiers.md), and [repository-impl.md](repository-impl.md) for
per-plugin configuration references.

## Three Plugin Groups

| Group | Purpose | Base class |
| --- | --- | --- |
| `pipe_ping.providers` | Poll CI/CD platforms | `BaseProvider` |
| `pipe_ping.repositories` | Persist and retrieve results | `AbstractDatabase` |
| `pipe_ping.notifiers` | Deliver alerts on transitions | `BaseNotifier` |

## Provider Plugin Contract

```python
class BaseProvider(ABC):
    @classmethod
    @abstractmethod
    def create(cls) -> "BaseProvider": ...

    @abstractmethod
    async def fetch_builds(self, repo: str) -> list[PipelineResult]: ...
```

- `create()` reads the plugin's own settings from the environment and returns a configured instance
- Must be read-only — no side effects, no state mutation
- Must handle pagination internally — callers receive the complete result list
- Must not propagate HTTP errors to the caller; catch and re-raise as typed exceptions
  (see [providers.md](providers.md) for the error handling convention)

Built-in registrations:

```toml
[project.entry-points."pipe_ping.providers"]
github = "pipe_ping.providers.github:GitHubProvider"
gitlab = "pipe_ping.providers.gitlab:GitLabProvider"
```

## Repository Plugin Contract

```python
class AbstractDatabase(ABC):
    @classmethod
    @abstractmethod
    def create(cls) -> "AbstractDatabase": ...

    @abstractmethod
    async def open(self) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...

    @abstractmethod
    def transaction(self) -> AbstractTransactionContext: ...
```

- `create()` reads the plugin's own settings from the environment and returns a configured instance
- `open` / `close` manage the connection lifecycle (pool, auth, etc.)
- `transaction()` is synchronous — it returns a context manager, it does not await one
- The context manager commits on clean exit and aborts on exception

```python
class AbstractTransaction(ABC):
    @abstractmethod
    async def write_one_pipeline_result(
        self, result: PipelineResult
    ) -> PipelineResultDocument: ...

    @abstractmethod
    async def read_one_pipeline_result(
        self, pipeline_id: str
    ) -> PipelineResultDocument | None: ...
```

Built-in repository registrations:

```toml
[project.entry-points."pipe_ping.repositories"]
mongo  = "pipe_ping.db.mongo:MongoDatabase"
```

Third-party and additional built-in backends register into the same group from their own
`pyproject.toml`. No changes to pipe-ping core are required.

## Notifier Plugin Contract

```python
class BaseNotifier(ABC):
    @classmethod
    @abstractmethod
    def create(cls) -> "BaseNotifier": ...

    @abstractmethod
    async def notify(self, event: StatusChangeEvent) -> None: ...
```

- `create()` reads the plugin's own settings from the environment and returns a configured instance
- Receives a `StatusChangeEvent`, not a raw `PipelineResultDocument`, so it has full
  transition context (old status, new status, build details)
- All I/O must be async — no blocking calls
- Failures must not propagate; the scheduler catches and logs them

Built-in registrations:

```toml
[project.entry-points."pipe_ping.notifiers"]
desktop = "pipe_ping.notifiers.desktop:DesktopNotifier"
```

## Writing a Third-Party Plugin

To add a new provider, repository, or notifier:

1. Create a Python package with a class implementing the appropriate ABC
2. Add the entry point registration to that package's `pyproject.toml`:

   ```toml
   [project.entry-points."pipe_ping.providers"]
   jenkins = "my_jenkins_plugin:JenkinsProvider"
   ```

3. Install it into the pipe-ping environment: `uv add ./my_jenkins_plugin` (or from PyPI)
4. Restart pipe-ping — the plugin is discovered automatically

No changes to pipe-ping source code are required.

## Error Handling in Discovery

The discovery function wraps each `ep.load()` in a `try/except ImportError` and logs a
warning for any plugin that fails to import. The remaining plugins continue loading.
A misconfigured third-party plugin must not prevent built-in plugins from working.

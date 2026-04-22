# Pipe-Ping — Architecture

> System design overview: what Pipe-Ping is, how it fits together, and where each piece lives.

## What Pipe-Ping Does

Pipe-Ping is an async Python service that:

1. **Polls** CI/CD platforms on a configurable interval via **provider** plugins
2. **Detects** status transitions — not just current state, but changes from the previous poll
3. **Persists** every result via **repository** plugins
4. **Fires** notifications via **notifier** plugins on actionable transitions only
5. **Exposes** a read-only REST API over the stored results
6. **Runs** as a CLI, a long-running API server, or inside Docker

All three plugin groups are optional extras. A bare `pip install pipe-ping` gives the
scheduler, API, and CLI, but no providers, notifiers, or persistent storage. The
in-memory repository ships with core so the service starts without any extras installed.
Capabilities are added via `pip install pipe-ping[github,mongodb,desktop]`.

## Data Flow

```text
[Provider plugins]        [Repository plugins]      [Notifier plugins]
  GitHubProvider    ──→   AbstractDatabase     ──→   DesktopNotifier
  GitLabProvider          (MongoDatabase)            WebhookNotifier
  JenkinsProvider   ──↘   AbstractTransaction  ──↗   EmailNotifier
  CircleCIProvider        read / upsert              SMSNotifier
         ↑                       ↑
   APScheduler            PipelineResultDocument
   (polling loop)         keyed by {repo}#{run_id}
         ↓
   StatusChangeEvent ──→ [all active notifiers]
```

Model transformation at each boundary:

| Stage | Model | Location |
| --- | --- | --- |
| Provider output | `PipelineResult` | `pipe_ping/models/provider.py` |
| Repository storage | `PipelineResultDocument` | `pipe_ping/models/db.py` |
| Transition event | `StatusChangeEvent` | `pipe_ping/models/events.py` |
| API response | `PipelineResultModel` | `pipe_ping/models/api.py` |
| Aggregated stats | `BuildSummary` | `pipe_ping/models/api.py` |

## Package Layout

```text
pipe_ping/
  __init__.py
  cli.py                typer app — pipe-ping CLI entry point
  main.py               startup: scheduler + API server
  config.py             PipePingSettings (core vars only), get_settings()
  scheduler.py          APScheduler polling loop + status-change detection
  db/
    __init__.py
    base.py             AbstractDatabase, AbstractTransactionContext, AbstractTransaction
    memory.py           InMemoryDatabase — ships with core, no extras required
    mongo.py            MongoDatabase — requires [mongodb] extra
  providers/
    __init__.py         entry-point discovery via importlib.metadata
    base.py             BaseProvider ABC
    github.py           GitHubProvider — requires [github] extra
    gitlab.py           GitLabProvider — requires [gitlab] extra
  notifiers/
    __init__.py         entry-point discovery
    base.py             BaseNotifier ABC
    desktop.py          DesktopNotifier — requires [desktop] extra
    webhook.py          WebhookNotifier — requires [webhook] extra
    email.py            EmailNotifier — requires [email] extra
    sms.py              SMSNotifier — requires [sms] extra
  models/
    __init__.py         re-exports all public model names
    common.py           PipelineStatus StrEnum
    provider.py         PipelineResult
    db.py               PipelineResultDocument
    api.py              PipelineResultModel, BuildSummary
    events.py           StatusChangeEvent
  api/
    __init__.py
    routers.py          FastAPI route handlers

tests/
  __init__.py
  conftest.py
  test_providers/
  test_notifiers/
  test_scheduler/
```

## Entry Points and Extras

All entry points are declared unconditionally in `pyproject.toml`. Optional dependencies
groups control which plugins can actually load — if a plugin's dependencies are not
installed, discovery catches the `ImportError` and skips it with a warning.

```toml
[project.optional-dependencies]
github  = ["aiohttp"]
gitlab  = ["aiohttp"]
mongodb = ["pymongo[async]"]
sqlite  = ["aiosqlite"]
desktop = ["desktop-notifier"]
webhook = ["aiohttp"]
email   = ["aiosmtplib"]
sms     = ["twilio"]

[project.entry-points."pipe_ping.providers"]
github  = "pipe_ping.providers.github:GitHubProvider"
gitlab  = "pipe_ping.providers.gitlab:GitLabProvider"

[project.entry-points."pipe_ping.repositories"]
memory  = "pipe_ping.db.memory:InMemoryDatabase"
mongodb = "pipe_ping.db.mongo:MongoDatabase"

[project.entry-points."pipe_ping.notifiers"]
desktop = "pipe_ping.notifiers.desktop:DesktopNotifier"
webhook = "pipe_ping.notifiers.webhook:WebhookNotifier"
email   = "pipe_ping.notifiers.email:EmailNotifier"
sms     = "pipe_ping.notifiers.sms:SMSNotifier"
```

`memory` is the only plugin that loads without any extra — it ships as part of core.
Third-party packages register into the same groups from their own `pyproject.toml`.
See [plugin-system.md](plugin-system.md) for the full extension guide.

## Terminology

| Term | Meaning |
| --- | --- |
| **provider** | Plugin that polls a CI/CD platform and returns `PipelineResult` objects |
| **repository** | The storage abstraction — named for what it does, not the backend. "Database" refers only to a specific backend (MongoDB, SQLite, etc.) |
| **notifier** | Plugin that delivers an alert when a status transition occurs |
| **extra** | An optional dependency group (`pip install pipe-ping[github]`) that unlocks a plugin |
| `_id` format | `"{repo}#{run_id}"` — composite string, unique across all providers |

## Toolchain

| Tool | Purpose |
| --- | --- |
| Python 3.13 | Runtime |
| uv | Package manager + virtualenv |
| asyncio | Async runtime for all I/O |
| aiohttp | Async HTTP client — pulled in by `[github]`, `[gitlab]`, `[webhook]` extras |
| pymongo `AsyncMongoClient` | Async MongoDB driver — pulled in by `[mongodb]` extra |
| FastAPI + uvicorn | REST API layer |
| APScheduler | Polling loop scheduling |
| Pydantic + pydantic-settings | Models + env config |
| desktop-notifier | Cross-platform toast notifications |
| typer | CLI interface |
| ruff | Linting + formatting |
| ty | Type checking |
| prek | Git hooks (ruff + ty) |
| Podman + podman-compose | Local MongoDB dev environment |
| Just | Task runner |
| pytest + pytest-asyncio | Testing |

## Related Docs

- [build-order.md](build-order.md) — phased implementation roadmap
- [plugin-system.md](plugin-system.md) — entry point discovery and plugin contracts
- [repository-impl.md](repository-impl.md) — repository layer ABI and MongoDB implementation
- [status-detection.md](status-detection.md) — core status-change detection logic
- [providers.md](providers.md) — provider plugin designs
- [notifiers.md](notifiers.md) — notifier plugin designs
- [deployment.md](deployment.md) — CLI, API server, and Docker run modes

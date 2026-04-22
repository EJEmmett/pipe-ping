# Pipe-Ping — Async CI/CD Pipeline Monitor

> "Ping your pipelines. Know before they break."

## What This Is

A locally-run async Python service that concurrently monitors CI/CD pipelines across
multiple providers (GitHub Actions, GitLab CI, and more). Providers, repositories, and
notifiers are all plugin-based via `importlib.metadata` entry points. Stores build history
via a repository plugin (MongoDB by default). Exposes a FastAPI REST API. Fires
cross-platform toast notifications — and other alerts — when pipeline status changes.
Status-change detection is the core logic: only transitions are acted on, not every poll.

## Tech Stack

| Tool | Purpose |
| ---- | ------- |
| Python 3.13 | Runtime |
| uv | Package manager + virtualenv |
| asyncio + aiohttp | Concurrent async HTTP polling |
| pymongo.AsyncMongoClient | Async MongoDB driver |
| FastAPI + uvicorn | REST API layer |
| APScheduler | Polling loop scheduling |
| Pydantic + pydantic-settings | Schemas + .env config |
| desktop-notifier | Cross-platform notifications (Windows/Linux/macOS via native APIs) |
| typer | CLI interface |
| ruff | Linting + formatting |
| ty | Type checking |
| prek | Git hooks (ruff + ty) |
| Podman + podman-compose | Local MongoDB dev environment |
| Just | Task runner |
| pytest + pytest-asyncio | Testing |

## Planning

> **Note for Claude:** When adding new design decisions, specs, or forward-looking content, create a file in `planning/` and add a pointer here — do not write planning content directly into this file.

See [`planning/`](planning/) for design docs:

- [`planning/architecture.md`](planning/architecture.md) — system overview, data flow, full package layout, toolchain
- [`planning/build-order.md`](planning/build-order.md) — phased implementation roadmap with checkpoints
- [`planning/plugin-system.md`](planning/plugin-system.md) — entry point discovery, all three plugin contracts, third-party extension guide
- [`planning/repository-impl.md`](planning/repository-impl.md) — repository layer ABI and MongoDB concrete implementation
- [`planning/status-detection.md`](planning/status-detection.md) — transition table, detection algorithm, `StatusChangeEvent` model, test requirements
- [`planning/providers.md`](planning/providers.md) — `BaseProvider` contract, GitHub and GitLab implementations, deferred providers
- [`planning/notifiers.md`](planning/notifiers.md) — `BaseNotifier` contract, all four notifier implementations
- [`planning/deployment.md`](planning/deployment.md) — CLI, API server, and Docker run modes

## Conventions

- **Type hints on every function signature** — no exceptions
- **Pydantic models for all data** — never raw dicts across boundaries
- **Async everywhere** — no blocking calls, no `time.sleep()`
- **No bare except clauses** — always catch specific exceptions
- **Abstract base classes** for providers, repositories, and notifiers — new ones are one file + one entry point
- **The storage abstraction is called a repository** — not a database; "database" refers only to the backend
- **Status change detection is the core logic** — only notify on transitions, not every poll
- **Environment variables via .env** — never hardcode secrets or tokens
- **Repository document IDs** — always use `_id` as string with format `{repo}#{run_id}`

## Environment Variables

All vars are prefixed `PIPE_PING_`. Nested settings use `__` as the delimiter.

```env
# CI/CD Provider Tokens
PIPE_PING_PROVIDER__GITHUB_TOKEN=ghp_...
PIPE_PING_PROVIDER__GITLAB_TOKEN=glpat-...

# MongoDB
PIPE_PING_DATABASE__MONGODB_URI=mongodb://localhost:27017
PIPE_PING_DATABASE__MONGODB_DB=pipe-ping

# Polling
PIPE_PING_POLL_INTERVAL_SECONDS=60

# Repos to watch (comma-separated owner/repo)
PIPE_PING_WATCH_REPOS=owner/repo1,owner/repo2
```

## Common Commands (via Just)

```bash
just install    # uv sync
just dev        # Start MongoDB + run pipe-ping watch
just test       # pytest
just lint       # ruff check + ruff format --check + ty check
just format     # ruff check --fix + ruff format
just mongo      # podman-compose up -d (MongoDB only)
just clean      # Stop containers, clear cache
```

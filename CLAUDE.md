# Pipe-Ping — Async CI/CD Pipeline Monitor

> "Ping your pipelines. Know before they break."

## What This Is

A locally-run async Python service that concurrently monitors CI/CD pipelines
across GitHub Actions and GitLab CI. Stores build history in MongoDB
via pymongo.AsyncMongoClient. Exposes a FastAPI REST API. Fires cross-platform toast
notifications on build status changes.

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

See [`planning/`](planning/) for work-in-progress docs:

- [`planning/build-order.md`](planning/build-order.md) — sequenced implementation plan
- [`planning/notifiers.md`](planning/notifiers.md) — email + SMS notifier design (deferred)
- [`planning/spec.md`](planning/spec.md) — project structure, CLI commands, API endpoints, testing approach
- [`planning/design-patterns.md`](planning/design-patterns.md) — plugin architecture, provider/notifier patterns, status change detection

## Conventions

- **Type hints on every function signature** — no exceptions
- **Pydantic models for all data** — never raw dicts across boundaries
- **Async everywhere** — no blocking calls, no `time.sleep()`
- **No bare except clauses** — always catch specific exceptions
- **Abstract base classes** for providers and notifiers — new ones are one file + one entry point
- **Status change detection is the core logic** — only notify on transitions, not every poll
- **Environment variables via .env** — never hardcode secrets or tokens
- **MongoDB document IDs** — always use `_id` as string (repo + run_id composite)

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

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
>
> **Precedence rule:** The `planning/` docs are the authoritative source of truth for architecture, interfaces, and conventions. If existing code (e.g. `config.py`, models, or entry points) conflicts with a planning doc, treat the planning doc as correct and the code as not yet updated. Do not propagate patterns from stale code — implement what the planning docs specify.

See [`planning/`](planning/) for design docs:

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

# Deployment

Pipe-Ping supports three run modes. All three share the same configuration via `.env`.

## Installation

A bare install includes the scheduler, API server, CLI, and the in-memory repository.
Extras unlock additional providers, persistent repositories, and notifiers:

```bash
pip install pipe-ping                              # core only
pip install pipe-ping[github,mongodb,desktop]     # common setup
pip install pipe-ping[github,gitlab,mongodb,desktop,email,sms]
```

With uv:

```bash
uv add pipe-ping
uv add "pipe-ping[github,mongodb,desktop]"
```

---

## Environment Configuration

All variables use the `PIPE_PING_` prefix. Core defines only two:

| Variable | Default | Description |
| --- | --- | --- |
| `PIPE_PING_WATCH_REPOS` | — | Comma-separated list of `owner/repo` to poll |
| `PIPE_PING_POLL_INTERVAL_SECONDS` | `60` | Seconds between poll cycles |

Each plugin defines and documents its own env vars under its own prefix. See
[providers.md](providers.md), [notifiers.md](notifiers.md), and
[repository-impl.md](repository-impl.md) for per-plugin configuration references.

Copy `.env.example` to `.env` and fill in the variables required by the extras you
have installed before running.

---

## CLI Mode

The primary run mode. Starts the polling scheduler and API server in a single process.

```bash
pipe-ping watch          # polling loop + API server (default port 8000)
pipe-ping status         # one-shot poll, print table to stdout, exit
pipe-ping add-repo       # add a repo to the watch list
pipe-ping list-repos     # print all watched repos
pipe-ping history        # recent build history for a repo
```

Entry point: `pipe_ping.cli:app` (typer). The `watch` command starts APScheduler and
uvicorn as concurrent async tasks in the same process — no separate workers needed.

**Prerequisites:** MongoDB must be reachable at `PIPE_PING_DATABASE__MONGODB_URI`.

**Local dev:**

```bash
just mongo    # start MongoDB via podman-compose
just dev      # mongo + pipe-ping watch
```

---

## API Server Mode

Headless REST API without the CLI. Suitable for environments where the process is managed
externally (e.g. systemd, supervisord).

```bash
uvicorn pipe_ping.api:app --host 0.0.0.0 --port 8000
```

The scheduler runs as a background task started in the FastAPI `lifespan` handler — no
separate worker process needed.

**Endpoints:**

```text
GET /health            200 OK + {"status": "ok"}
GET /builds            list[PipelineResultModel] — all recent builds
GET /builds/{repo}     list[PipelineResultModel] — builds for one repo
GET /summary           list[BuildSummary] — failure rates, avg duration per repo
```

---

## Docker Mode

Both the pipe-ping service and MongoDB run as containers managed by Docker Compose.

```yaml
services:
  mongo:
    image: mongo:8
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 5s
      retries: 5

  pipe-ping:
    build: .
    depends_on:
      mongo:
        condition: service_healthy
    environment:
      PIPE_PING_DATABASE__MONGODB_URI: mongodb://mongo:27017
      PIPE_PING_DATABASE__MONGODB_DB: pipe-ping
    env_file: .env
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
```

**Notes:**

- Desktop notifications are unavailable in headless containers. The notifier discovery
  function handles this gracefully — it logs a warning and skips the desktop plugin if
  no display is available.
- Secrets (tokens) should be passed via environment variables or a Docker secrets mount,
  not baked into the image.

**Local development with Podman:**

```bash
just mongo     # podman-compose up -d (MongoDB only)
just dev       # mongo + uv run pipe-ping watch
just clean     # stop containers, clear __pycache__ and pytest/ruff caches
```

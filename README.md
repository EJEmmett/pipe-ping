# Pipe-Ping

> Ping your pipelines. Know before they break.

Async CI/CD pipeline monitor with plugin capabilities to define providers and notifiers.

## Prerequisites

- [Python 3.13](https://www.python.org/downloads/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [Podman Desktop](https://podman-desktop.io/) (for local MongoDB)
- [Just](https://just.systems/man/en/packages.html)

## Getting Started

1. **Clone and install dependencies**

   ```bash
   git clone <repo-url>
   cd Pipe-Ping
   just install
   ```

2. **Configure environment**

   ```bash
   cp .env.example .env
   ```

   Fill in your tokens in `.env`:

   ```env
   GITHUB_TOKEN=ghp_...
   GITLAB_TOKEN=glpat-...
   WATCH_REPOS=owner/repo1,owner/repo2
   ```

3. **Start MongoDB**

   ```bash
   just mongo
   ```

4. **Run Pipe-Ping**

   ```bash
   just dev        # MongoDB + polling loop + API server
   ```

   The API is available at `http://localhost:8000`.

## CLI

```bash
pipe-ping watch              # start polling loop + API server
pipe-ping status             # current health of all watched repos
pipe-ping add-repo           # add a repo to the watch list
pipe-ping list-repos         # list all watched repos
pipe-ping history <repo>     # build history for a repo
```

## API

```
GET /builds            # all recent builds
GET /builds/{repo}     # builds for a specific repo
GET /summary           # failure rates, avg duration
GET /health            # service health check
```

## Just Recipes

```bash
just install    # uv sync
just dev        # start MongoDB + pipe-ping watch
just test       # pytest
just lint       # ruff check + format check + ty check
just format     # ruff check --fix + ruff format
just mongo      # docker compose up -d
just clean      # stop containers, clear cache
```

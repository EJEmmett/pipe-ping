# Build Order

Phases are sequential — each depends on the one before. Complete and validate each phase
before moving to the next. The checkpoint describes the minimum proof a phase is done.

---

## Phase 1 — Foundation

**Files:** `pipe_ping/models/`, `pipe_ping/config.py`

Pydantic models for all data boundaries and the pydantic-settings configuration layer.
`get_settings()` returns a cached singleton loaded from the `.env` file.

**Checkpoint:** `from pipe_ping.models import PipelineResult, PipelineResultDocument` and
`from pipe_ping.config import get_settings` both succeed without error.

---

## Phase 2 — Repository Layer

**Files:** `pipe_ping/repository/base.py`, `pipe_ping/repository/memory.py`, `pipe_ping/models/events.py`

Abstract repository layer (`AbstractRepository`, `AbstractTransactionContext`,
`AbstractTransaction`) and the in-memory concrete implementation. The in-memory repository
ships with core — no extras required — and serves as the default when no persistent backend
is installed. All writes are upserts keyed by `{repo}#{run_id}`. Also add
`StatusChangeEvent` to `pipe_ping/models/events.py` so the scheduler and notifiers share
one import location.

**Checkpoint:** unit tests prove that `MemoryRepository` round-trips a
`write_one_pipeline_result` / `read_one_pipeline_result` pair and preserves all fields
including `raw`. Run without any optional extras installed.

---

## Phase 3 — Provider Plugin Infrastructure

**Files:** `pipe_ping/providers/__init__.py`, `pipe_ping/providers/base.py`

Discovery function loads all `pipe_ping.providers` entry points into a dict at startup.
`BaseProvider` ABC defines the single required method. Discovery wraps each load in a
`try/except ImportError` so a broken plugin does not prevent others from loading.

**Checkpoint:** discovery function returns a dict containing the built-in provider names.
An intentionally broken entry point is skipped with a logged warning.

---

## Phase 3a — GitHub Provider

**Files:** `pipe_ping/providers/github.py`

`GitHubProvider` uses `aiohttp` to call the GitHub Actions REST API. Handles pagination
transparently. Maps all GitHub status + conclusion combinations to `PipelineStatus`.

**Checkpoint:** mock HTTP test (via `aioresponses`) proves `GitHubProvider.fetch_builds`
returns a `list[PipelineResult]` with correctly mapped `status` values. Test at least one
successful run, one failed run, and one in-progress run.

---

## Phase 5 — Scheduler + Status-Change Detection

**Files:** `pipe_ping/scheduler.py`

APScheduler polling loop. Calls all active providers per watched repo, reads the previous
result from the repository, writes the update, and fires notifiers on actionable
transitions. See [status-detection.md](status-detection.md) for the full transition table
and detection algorithm.

**Checkpoint:** unit tests (mocked provider + repository + notifiers) prove:

- Notifier fires exactly once per actionable transition
- Notifier does not fire when status is unchanged
- Notifier failures are caught and logged — scheduler loop continues

---

## Phase 6 — Notifier Plugin Infrastructure

**Files:** `pipe_ping/notifiers/__init__.py`, `pipe_ping/notifiers/base.py`

Discovery mirrors provider discovery. `BaseNotifier` defines `notify(event)`.

**Checkpoint:** discovery function returns a dict containing the built-in notifier names.
An intentionally broken entry point is skipped with a logged warning.

---

## Phase 6a — Desktop Notifier

**Files:** `pipe_ping/notifiers/desktop.py`

Fires a cross-platform toast via the `desktop-notifier` library. On headless systems where
no display is available, the plugin load fails gracefully with a warning.

**Checkpoint:** injecting a `StatusChangeEvent` into `DesktopNotifier.notify` produces a
visible toast (manual test). Unit test mocks the `desktop-notifier` send call.

---

## Phase 7 — REST API

**Files:** `pipe_ping/api/__init__.py`, `pipe_ping/api/routers.py`

Four read-only endpoints backed directly by the repository — no scheduler involvement.

```text
GET /health            service health check
GET /builds            all recent builds across all repos
GET /builds/{repo}     build history for a specific repo
GET /summary           failure rates, average duration per repo
```

**Checkpoint:** `GET /health` returns 200. `GET /builds` returns a valid JSON array of
`PipelineResultModel` objects.

---

## Phase 8 — CLI + Entry Point

**Files:** `pipe_ping/cli.py`, `pipe_ping/main.py`

Typer CLI wires together the scheduler, API server, and repository. `main.py` is the
startup sequence called by `pipe-ping watch`.

```text
pipe-ping watch          start polling loop + API server
pipe-ping status         one-shot poll, print table, exit
pipe-ping add-repo       add a repo to PIPE_PING_WATCH_REPOS
pipe-ping list-repos     list all watched repos
pipe-ping history        build history for a repo
```

**Checkpoint:** `pipe-ping watch` starts, polls at least one cycle against a real provider
token, and writes a result to the repository. `pipe-ping status` exits cleanly.

---

## Phase 9 — Deferred

Lower priority. Do not start until Phase 8 is complete and stable.

- **GitLab provider** — calls GitLab Pipelines REST API; resolves `owner/name` to a project ID via the projects API and caches it for the lifetime of the instance; `[gitlab]` extra
- **MongoDB repository** — `pymongo[async]`; `[mongodb]` extra
- **Jenkins provider** — requires per-installation base URL + username/token
- **CircleCI provider** — v2 API, `CIRCLE_TOKEN` header
- **Webhook notifier** — POST `StatusChangeEvent` as JSON to a configurable URL; `[webhook]` extra
- **Email notifier** — `aiosmtplib`, SMTP credentials in `NotifierSettings`; `[email]` extra
- **SMS notifier** — Twilio (preferred) or AWS SNS; `[sms]` extra
- **SQLite repository** — `aiosqlite`; `[sqlite]` extra

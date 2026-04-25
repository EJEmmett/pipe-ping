# Pipe-Ping — Architecture

An async Python service that polls CI/CD pipelines, detects status transitions, persists
results, and fires notifications. All three extension points — providers, repositories,
notifiers — are plugins discovered via `importlib.metadata` entry points.

## Startup Sequence

1. Load core settings (`PIPE_PING_POLL_INTERVAL_SECONDS`)
2. Discover and instantiate repository plugin (falls back to in-memory)
3. Discover provider plugins — each registers a hook bundle on load
4. Discover and instantiate notifier plugins
5. Start APScheduler + FastAPI in the same async process

## Provider Hook Bundle

Providers are not just functions — they register a bundle of hooks that define how their
data moves across each boundary:

```python
class ProviderHooks:
    provider_to_document: Callable[[NativeResult], Document]
    document_to_model:    Callable[[Document], APIModel]
    provider_to_message:  Callable[[Document], str]
```

Providers own the transformation at each boundary. Core dispatches by looking up the
registered hooks for a given document type.

## Poll Cycle

APScheduler fires once per `(provider, repo)` pair every `POLL_INTERVAL_SECONDS`:

1. Provider calls platform API → returns list of native result objects
2. For each result:
   - Call `provider_to_document` → document for storage
   - Read previous document from repository by `{repo}#{run_id}`
   - Upsert current document
   - `should_notify(previous_status, current_status)` — operates on `PipelineStatus`
   - If notifiable: call `provider_to_message` → string, build `StatusChangeEvent`, fire notifiers

## Status Detection

The only settled business logic. `PipelineStatus` is a `StrEnum`:
`PENDING | RUNNING | SUCCESS | FAILURE | CANCELLED | SKIPPED | UNKNOWN`

Providers normalize their native statuses to this enum. `should_notify` compares
previous and current — only transitions trigger notifications, never repeated states.
See `status-detection.md` for the full transition table.

## Data Boundaries

| Boundary          | Responsibility                        |
| ----------------- | ------------------------------------- |
| Provider output   | Native platform type                  |
| Repository        | Stable, queryable document            |
| API response      | Provider-native, ergonomic shape      |
| Notification      | Human-readable string from `provider_to_message` |

## Plugin Discovery

All entry points declared in `pyproject.toml`. Missing dependencies cause the plugin to
be skipped with a warning — not a crash.

```toml
[project.entry-points."pipe_ping.providers"]
[project.entry-points."pipe_ping.repositories"]
[project.entry-points."pipe_ping.notifiers"]
```

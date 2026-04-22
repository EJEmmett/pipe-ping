# Status-Change Detection

Status-change detection is the core business logic of Pipe-Ping. The scheduler polls
providers on every interval, but notifications fire only when a pipeline's status
transitions — not on every poll. This keeps alerts actionable and avoids noise.

## Why Transitions, Not Snapshots

Every poll yields the current status of a run. Notifying on every poll would send a
"FAILURE" alert on every cycle until the run is fixed. What matters is the moment the
status changes — the regression, the recovery, the first result on a new run.

## `PipelineStatus` Values

`PipelineStatus` is a `StrEnum` defined in `pipe_ping/models/common.py`:

| Value | Meaning |
| --- | --- |
| `PENDING` | Queued, not yet started |
| `RUNNING` | Currently executing |
| `SUCCESS` | Completed successfully |
| `FAILURE` | Completed with errors |
| `CANCELLED` | Manually stopped |
| `SKIPPED` | Bypassed (e.g. branch filter) |
| `UNKNOWN` | Provider response couldn't be mapped |

## Transition Table

| Previous → Current | Action | Rationale |
| --- | --- | --- |
| `PENDING` → `RUNNING` | Silent | Normal progress, not actionable |
| `PENDING` → `SUCCESS` | **Notify** | First result: build passed |
| `PENDING` → `FAILURE` | **Notify** | First result: build failed |
| `RUNNING` → `SUCCESS` | **Notify** | Build completed successfully |
| `RUNNING` → `FAILURE` | **Notify** | Build broke — most important signal |
| `FAILURE` → `SUCCESS` | **Notify** | Recovery — equally important |
| `SUCCESS` → `FAILURE` | **Notify** | Regression — critical |
| `SUCCESS` → `SUCCESS` | Silent | No change |
| `FAILURE` → `FAILURE` | Silent | Already notified on first failure |
| any → `CANCELLED` | Silent | User action, not a build event |
| any → `SKIPPED` | Silent | Expected, not actionable |
| any → `UNKNOWN` | Silent | Mapping gap — log a warning instead |
| `None` (first poll) → any terminal | **Notify** | First result for this run |
| `None` (first poll) → `RUNNING` | Silent | Don't alert on in-progress runs at startup |

## `StatusChangeEvent` Model

Defined in `pipe_ping/models/events.py`:

```python
class StatusChangeEvent(BaseModel):
    repo: str
    provider: str
    previous_status: PipelineStatus | None   # None on first poll
    current_status: PipelineStatus
    build: PipelineResultDocument
```

This model is passed to `BaseNotifier.notify()`. Notifiers receive the full transition
context — not just the current build — so they can compose meaningful messages.

## Detection Algorithm

Run once per poll cycle, per watched repo, per provider:

```python
async def process_builds(
    provider: BaseProvider,
    repo: str,
    db: AbstractDatabase,
    notifiers: list[BaseNotifier],
) -> None:
    builds = await provider.fetch_builds(repo)

    async with db.transaction() as tx:
        for build in builds:
            pipeline_id = f"{build.repo}#{build.id}"
            previous = await tx.read_one_pipeline_result(pipeline_id)
            previous_status = previous.status if previous else None

            doc = await tx.write_one_pipeline_result(build)

            if should_notify(previous_status, doc.status):
                event = StatusChangeEvent(
                    repo=repo,
                    provider=build.provider,
                    previous_status=previous_status,
                    current_status=doc.status,
                    build=doc,
                )
                await fire_notifiers(notifiers, event)


def should_notify(
    previous: PipelineStatus | None,
    current: PipelineStatus,
) -> bool:
    if current in (PipelineStatus.CANCELLED, PipelineStatus.SKIPPED, PipelineStatus.UNKNOWN):
        return False
    if current == PipelineStatus.RUNNING and previous is None:
        return False  # startup: run already in progress
    return previous != current
```

## Concurrency Considerations

APScheduler fires one coroutine per (provider, repo) pair. These run concurrently. Because
each pipeline result is identified by a unique `_id` (`{repo}#{run_id}`), concurrent writes
to different runs do not interfere.

The read-then-write sequence is protected within a transaction. A second concurrent poll
for the same run_id will see the committed write from the first poll and treat it as the
previous state. The worst case is a duplicate notification on the same transition, which
is acceptable.

## Notifier Error Isolation

All notifiers are called in sequence. A failure in one notifier must not prevent others
from running and must not crash the scheduler:

```python
async def fire_notifiers(
    notifiers: list[BaseNotifier],
    event: StatusChangeEvent,
) -> None:
    for notifier in notifiers:
        try:
            await notifier.notify(event)
        except Exception as exc:
            logger.warning("notifier %s failed: %s", type(notifier).__name__, exc)
```

## Test Requirements

- Parametrize all (previous, current) pairs from the transition table
- Assert `should_notify` returns `True` exactly for the "Notify" rows
- Assert notifier mock is called exactly once per actionable transition
- Assert notifier mock is not called on silent transitions
- Test idempotency: two consecutive polls with the same status → zero notifications
- Test startup case: `previous=None, current=RUNNING` → no notification
- Test startup case: `previous=None, current=FAILURE` → notification fires

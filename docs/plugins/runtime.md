# How plugins run

## Polling

Pipe-Ping polls each provider every 60 seconds. Providers are polled
concurrently. On each poll, Pipe-Ping:

1. Calls the provider's `poll()`.
2. Passes the results to the repository's `save()`.
3. Passes the results that `save()` returns to each notifier's `notify()`, one
   notifier at a time. If `save()` returns an empty list, this step is skipped.

Plugin methods can be synchronous. Pipe-Ping runs them in a worker thread so
they do not block other plugins.

## Timeouts and errors

When a method raises an exception or times out, Pipe-Ping logs the error and
continues:

| Method | Timeout | On error or timeout |
| --- | --- | --- |
| `setup()` | 10 seconds | The plugin is skipped |
| `poll()` | 60 seconds | The poll ends. The provider is polled again 60 seconds later |
| `save()` | 60 seconds | The poll ends. The provider is polled again 60 seconds later |
| `notify()` | 60 seconds | The remaining notifiers are still called |
| `teardown()` | 10 seconds | The remaining plugins are still torn down |

If every plugin in a group is skipped, Pipe-Ping exits.

## Repository behavior

A repository's `save()` receives the results of one provider's poll and returns
the results to notify about. The built-in repositories:

- Return pipeline runs that are new or whose status has changed since the last
  save.
- Return an empty list the first time they see a provider, so pipeline runs
  that already exist at startup are not reported.

A custom repository should also skip the first save for each provider.
Otherwise, every recent pipeline run is reported the first time it runs.

## Notifier behavior

Notifiers receive every result the repository returns, including `PENDING` and
`RUNNING` changes. To report only finished pipeline runs, filter the results:

```python
from pipe_ping.models.provider import PipelineResult, PipelineStatus

FINISHED = {PipelineStatus.SUCCESS, PipelineStatus.FAILURE, PipelineStatus.CANCELLED}


class ExampleNotifier:
    async def notify(self, results: list[PipelineResult]) -> None:
        for result in results:
            if result.status in FINISHED:
                print(f"{result.repo} {result.branch}: {result.status}")
```

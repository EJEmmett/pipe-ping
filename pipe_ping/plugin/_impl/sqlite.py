import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiosqlite

from pipe_ping.tools import get_settings

if TYPE_CHECKING:
    from pipe_ping.models.provider import PipelineResult
    from pipe_ping.tools.settings import SqliteSettings

CREATE_RUNS_TABLE = """
CREATE TABLE IF NOT EXISTS runs (
    provider    TEXT NOT NULL,
    id          TEXT NOT NULL,
    repo        TEXT NOT NULL,
    branch      TEXT NOT NULL,
    commit_sha  TEXT NOT NULL,
    status      TEXT NOT NULL,
    url         TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    started_at  TEXT,
    finished_at TEXT,
    raw         TEXT NOT NULL,
    PRIMARY KEY (provider, id)
)
"""

UPSERT_RUN = """
INSERT INTO runs (
    provider, id, repo, branch, commit_sha, status, url,
    created_at, started_at, finished_at, raw
) VALUES (
    :provider, :id, :repo, :branch, :commit_sha, :status, :url,
    :created_at, :started_at, :finished_at, :raw
)
ON CONFLICT (provider, id) DO UPDATE SET
    repo        = excluded.repo,
    branch      = excluded.branch,
    commit_sha  = excluded.commit_sha,
    status      = excluded.status,
    url         = excluded.url,
    created_at  = excluded.created_at,
    started_at  = excluded.started_at,
    finished_at = excluded.finished_at,
    raw         = excluded.raw
"""


class SqliteRepository:
    """Store the latest result for each pipeline run in a SQLite database.

    ``save`` returns the pipeline runs that are new or changed status. The
    first save for a provider with no stored pipeline runs records them and
    returns nothing.
    """

    settings: "SqliteSettings"
    connection: aiosqlite.Connection | None

    def __init__(self) -> None:
        self.settings = get_settings().sqlite
        self.connection = None

    async def setup(self) -> None:
        path = Path(self.settings.path)
        path.parent.mkdir(parents=True, exist_ok=True)

        self.connection = await aiosqlite.connect(path)
        await self.connection.execute(CREATE_RUNS_TABLE)
        await self.connection.commit()

    async def teardown(self) -> None:
        if self.connection is not None:
            await self.connection.close()

    async def save(self, results: "list[PipelineResult]") -> "list[PipelineResult]":
        """Store *results* in one transaction; return new or changed pipeline runs."""
        if self.connection is None:
            raise RuntimeError("SqliteRepository.setup() must be called before saving")

        try:
            known_providers = await providers_with_runs(
                self.connection, {result.provider for result in results}
            )

            changed: list[PipelineResult] = []
            for result in results:
                previous_status = await stored_status(
                    self.connection, result.provider, result.id
                )
                await self.connection.execute(UPSERT_RUN, to_row(result))

                if result.provider not in known_providers:
                    continue
                if previous_status != result.status.value:
                    changed.append(result)

            await self.connection.commit()
        except Exception:
            await self.connection.rollback()
            raise

        return changed


async def providers_with_runs(
    connection: aiosqlite.Connection, providers: set[str]
) -> set[str]:
    """Return which of *providers* already have pipeline runs stored."""
    known: set[str] = set()
    for provider in providers:
        async with connection.execute(
            "SELECT 1 FROM runs WHERE provider = ? LIMIT 1", (provider,)
        ) as cursor:
            if await cursor.fetchone() is not None:
                known.add(provider)

    return known


async def stored_status(
    connection: aiosqlite.Connection, provider: str, run_id: str
) -> str | None:
    async with connection.execute(
        "SELECT status FROM runs WHERE provider = ? AND id = ?", (provider, run_id)
    ) as cursor:
        row = await cursor.fetchone()

    return None if row is None else row[0]


def to_row(result: "PipelineResult") -> dict[str, Any]:
    row = result.model_dump(mode="json")
    row["raw"] = json.dumps(row["raw"])
    return row

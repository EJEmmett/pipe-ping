# Repository Layer — Implementation

The storage abstraction is called the **repository layer**. The word "database" refers
only to a specific backend (MongoDB, SQLite, etc.). Callers always interact with the ABCs
(`AbstractRepository`, `AbstractTransaction`) — never with concrete classes directly.

## Two-Layer ABI

```text
AbstractRepository          AbstractTransactionContext     AbstractTransaction
  open()            ──→     __aenter__()          ──→     write_one_pipeline_result()
  close()                   __aexit__()                   read_one_pipeline_result()
  transaction()     ──→   (context manager)
```

### `AbstractRepository`

```python
class AbstractRepository(ABC):
    _opened: bool = False

    @classmethod
    @abstractmethod
    def create(cls) -> "Self": ...

    async def open(self) -> None:
        await self._open()
        self._opened = True

    async def close(self) -> None:
        self._require_open()
        await self._close()
        self._opened = False

    def transaction(self) -> AbstractTransactionContext:
        self._require_open()
        return self._transaction()

    def _require_open(self) -> None:
        if not self._opened:
            raise RuntimeError(f"{type(self).__name__}.open() must be called first")

    @abstractmethod
    async def _open(self) -> None: ...

    @abstractmethod
    async def _close(self) -> None: ...

    @abstractmethod
    def _transaction(self) -> AbstractTransactionContext: ...
```

`create()` reads the plugin's own settings from the environment and returns a configured
instance. Core calls this once at startup, then calls `open()` to establish the connection,
and passes the instance to the scheduler and API.

`open` / `close` / `transaction` are **concrete** on the ABC — they enforce the lifecycle
invariant (`open()` before `close()` or `transaction()`), then delegate to the abstract
`_open()` / `_close()` / `_transaction()` hooks that subclasses implement. Calling
`close()` or `transaction()` before `open()` raises `RuntimeError`.

`transaction` is **synchronous** — it returns a context manager, it does not await one.

### `AbstractTransactionContext`

```python
class AbstractTransactionContext(AbstractAsyncContextManager):
    @abstractmethod
    async def __aenter__(self) -> "AbstractTransaction": ...

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None: ...
```

On `__aexit__`: commit if no exception, abort if an exception is active, then release
the session. Call site pattern:

```python
async with db.transaction() as tx:
    doc = await tx.read_one_pipeline_result(pipeline_id)
```

### `AbstractTransaction`

```python
class AbstractTransaction(ABC):
    @abstractmethod
    async def write_one_pipeline_result(
        self, result: PipelineResult
    ) -> PipelineResultDocument: ...

    @abstractmethod
    async def read_one_pipeline_result(
        self, pipeline_id: str
    ) -> PipelineResultDocument | None: ...
```

### `_id` Composite Key

All writes are **upserts**, never bare inserts. The document key is:

```python
_id = f"{result.repo}#{result.id}"   # e.g. "owner/repo#12345678"
```

This key is globally unique across all providers and repos. Re-polling the same run
overwrites the previous document — idempotent by design.

### `PipelineResultDocument.from_result()`

`PipelineResultDocument` carries a classmethod factory that constructs the document from
a `PipelineResult`, computing the composite `_id` and copying all remaining fields via
`model_dump`. Both `InMemoryTransaction` and `MongoTransaction` use this factory instead
of constructing the document inline — keeping the key-computation logic in one place.

```python
@classmethod
def from_result(cls, result: "PipelineResult") -> "PipelineResultDocument":
    return cls(
        _id=f"{result.repo}#{result.id}",
        **result.model_dump(exclude={"id"}),
    )
```

---

## In-Memory Concrete Implementation

`InMemoryRepository` ships with core — no extras required. It holds all documents in a
plain dict for the lifetime of the process. Data does not survive restarts. Its primary
use is as the default backend when no persistent repository is installed, and as the
test double for scheduler unit tests.

`create()` requires no configuration and returns a new instance immediately.

```python
class InMemoryRepository(AbstractRepository):
    @classmethod
    def create(cls) -> "Self":
        return cls()

    async def _open(self) -> None:
        self._store: dict[str, PipelineResultDocument] = {}

    async def _close(self) -> None:
        self._store.clear()

    def _transaction(self) -> "InMemoryTransactionContext":
        return InMemoryTransactionContext(self._store)
```

`InMemoryTransactionContext` and `InMemoryTransaction` follow the same two-layer pattern
as the MongoDB implementation. Because there are no concurrent writers within a single
async process, the transaction context needs no locking — `__aenter__` simply returns
an `InMemoryTransaction` wrapping the shared store dict, and `__aexit__` is a no-op on
clean exit.

```python
class InMemoryTransaction(AbstractTransaction):
    def __init__(self, store: dict[str, PipelineResultDocument]) -> None:
        self._store = store

    async def write_one_pipeline_result(
        self, result: PipelineResult
    ) -> PipelineResultDocument:
        doc = PipelineResultDocument.from_result(result)
        self._store[doc.id] = doc
        return doc

    async def read_one_pipeline_result(
        self, pipeline_id: str
    ) -> PipelineResultDocument | None:
        return self._store.get(pipeline_id)
```

---

## MongoDB Concrete Implementation

### `MongoRepository`

Implements `AbstractRepository`. Requires the `[mongodb]` extra. `create()` reads
`MongoRepositorySettings` from the environment and stores the URI and database name.
`open()` establishes the `AsyncMongoClient` connection using those values.
`transaction()` is synchronous and returns a `MongoTransactionContext`.

```python
class MongoRepositorySettings(BaseSettings):
    uri: str = "mongodb://localhost:27017"
    db: str = "pipe-ping"

    model_config = SettingsConfigDict(
        env_prefix="PIPE_PING_MONGODB_",
        env_file=".env",
    )
```

| Env var | Required | Description |
| --- | --- | --- |
| `PIPE_PING_MONGODB_URI` | no (default `mongodb://localhost:27017`) | MongoDB connection string |
| `PIPE_PING_MONGODB_DB` | no (default `pipe-ping`) | Database name |

```python
class MongoRepository(AbstractRepository):
    def __init__(self, uri: str, db: str) -> None:
        self._uri = uri
        self._db_name = db

    @classmethod
    def create(cls) -> "Self":
        settings = MongoRepositorySettings()
        return cls(uri=settings.uri, db=settings.db)

    async def _open(self) -> None:
        self.client = AsyncMongoClient(self._uri)
        self.database = self.client.get_database(self._db_name)

    async def _close(self) -> None:
        await self.client.close()

    def _transaction(self) -> "MongoTransactionContext":
        return MongoTransactionContext(self.database)
```

### `MongoTransactionContext`

Wraps `client.start_session()`. `__aenter__` starts the session, begins a transaction,
and yields a `MongoTransaction`. `__aexit__` commits on clean exit and aborts on exception.

```python
class MongoTransactionContext(AbstractTransactionContext):
    def __init__(self, database: AsyncDatabase) -> None:
        self.database = database
        self._session: AsyncClientSession | None = None

    async def __aenter__(self) -> "MongoTransaction":
        self._session = await self.database.client.start_session()
        self._session.start_transaction()
        collection = self.database["pipeline_results"]
        return MongoTransaction(collection, self._session)

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._session is None:
            return
        try:
            if exc_type is None:
                await self._session.commit_transaction()
            else:
                await self._session.abort_transaction()
        finally:
            await self._session.end_session()
            self._session = None
```

### `MongoTransaction`

Implements `AbstractTransaction`. Holds the active `AsyncClientSession` and a reference
to the `pipeline_results` collection.

`write_one_pipeline_result` constructs a `PipelineResultDocument`, then upserts by `_id`
using the active session. The `_id` is the composite `{repo}#{run_id}` key.

`read_one_pipeline_result` calls `find_one({"_id": pipeline_id}, session=session)` and
returns a `PipelineResultDocument`, or `None` if not found.

```python
class MongoTransaction(AbstractTransaction):
    def __init__(self, collection: AsyncCollection, session: AsyncClientSession) -> None:
        self.collection = collection
        self.session = session

    async def write_one_pipeline_result(
        self, result: PipelineResult
    ) -> PipelineResultDocument:
        doc = PipelineResultDocument.from_result(result)
        await self.collection.update_one(
            {"_id": doc.id},
            {"$set": doc.model_dump(by_alias=True)},
            upsert=True,
            session=self.session,
        )
        return doc

    async def read_one_pipeline_result(
        self, pipeline_id: str
    ) -> PipelineResultDocument | None:
        raw = await self.collection.find_one(
            {"_id": pipeline_id}, session=self.session
        )
        if raw is None:
            return None
        return PipelineResultDocument.model_validate(raw)
```

---

## Deferred

- `read_many_pipeline_results` — query by repo, branch, status, or time range
- Schema migrations
- SQLite and JSON backends (see Phase 10 in [build-order.md](build-order.md))

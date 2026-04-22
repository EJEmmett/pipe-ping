# Providers

A provider polls one CI/CD platform and returns a list of pipeline results. Each provider
is a plugin — one file, one entry point. No changes to the core are needed to add a new one.

## `BaseProvider` ABC

```python
# pipe_ping/providers/base.py
class BaseProvider(ABC):
    @classmethod
    @abstractmethod
    def create(cls) -> "BaseProvider": ...

    @abstractmethod
    async def fetch_builds(self, repo: str) -> list[PipelineResult]: ...
```

- `create()` reads the provider's own settings from the environment and returns a
  configured instance. Core calls this once at startup and passes the instance around.
- `repo` is always `"owner/name"` format
- Must handle pagination internally — callers receive the full result list
- Must be stateless and read-only — no side effects
- Must not let HTTP errors propagate (see error handling below)

## `PipelineResult` Field Mapping

Every provider must map its API response to `PipelineResult` (`pipe_ping/models/provider.py`):

| Field | Type | Convention |
| --- | --- | --- |
| `id` | `str` | Platform-native run ID, as a string |
| `provider` | `str` | Entry point name: `"github"`, `"gitlab"`, etc. |
| `repo` | `str` | `"owner/name"` — passed in from the caller |
| `branch` | `str` | Ref name without `refs/heads/` prefix |
| `commit_sha` | `str` | Full 40-character SHA |
| `status` | `PipelineStatus` | Mapped from platform status string (see tables below) |
| `url` | `str` | Direct link to the run in the platform UI |
| `created_at` | `datetime` | When the run was created (UTC, timezone-aware) |
| `started_at` | `datetime \| None` | When execution began |
| `finished_at` | `datetime \| None` | When execution ended |
| `raw` | `dict` | Full deserialized API response — no filtering |

## Error Handling Convention

| HTTP status | Action |
| --- | --- |
| 401 / 403 | Log at ERROR, raise `ProviderAuthError` — halts this provider's polling |
| 429 | Log at WARNING, return empty list — skip this poll cycle |
| 5xx | Log at WARNING, return empty list — skip this poll cycle |
| Network error | Log at WARNING, return empty list — skip this poll cycle |

Never let provider exceptions reach the scheduler loop. The scheduler catches
`ProviderAuthError` and disables the provider until restart. All other errors are
absorbed by returning an empty list from `fetch_builds`.

---

## GitHub Actions Provider

**Entry point:** `github = "pipe_ping.providers.github:GitHubProvider"`

**Endpoint:** `GET https://api.github.com/repos/{owner}/{repo}/actions/runs`

**Configuration:**

```python
class GitHubSettings(BaseSettings):
    token: str

    model_config = SettingsConfigDict(
        env_prefix="PIPE_PING_GITHUB_",
        env_file=".env",
    )
```

| Env var | Required | Description |
| --- | --- | --- |
| `PIPE_PING_GITHUB_TOKEN` | yes | Personal access token (`ghp_...`) |

**Auth:** `Authorization: Bearer {token}` header, token sourced from `GitHubSettings`

**Key query params:**

- `per_page=100` — max page size
- `page=N` — iterate until no `next` link in the `Link` header

**Status mapping:**

| GitHub `status` | GitHub `conclusion` | `PipelineStatus` |
| --- | --- | --- |
| `queued` | — | `PENDING` |
| `in_progress` | — | `RUNNING` |
| `completed` | `success` | `SUCCESS` |
| `completed` | `failure` | `FAILURE` |
| `completed` | `cancelled` | `CANCELLED` |
| `completed` | `skipped` | `SKIPPED` |
| `completed` | `timed_out` | `FAILURE` |
| `completed` | `action_required` | `UNKNOWN` |
| `completed` | `neutral` | `UNKNOWN` |
| anything else | anything else | `UNKNOWN` |

**Notes:**

- `run.head_branch` → `branch`
- `run.head_sha` → `commit_sha`
- `run.html_url` → `url`
- `run.id` (integer) → `str(run["id"])` for the `id` field

---

## GitLab CI Provider

**Entry point:** `gitlab = "pipe_ping.providers.gitlab:GitLabProvider"`

**Endpoint:** `GET https://gitlab.com/api/v4/projects/{project_id}/pipelines`

**Configuration:**

```python
class GitLabSettings(BaseSettings):
    token: str

    model_config = SettingsConfigDict(
        env_prefix="PIPE_PING_GITLAB_",
        env_file=".env",
    )
```

| Env var | Required | Description |
| --- | --- | --- |
| `PIPE_PING_GITLAB_TOKEN` | yes | Personal access token (`glpat-...`) |

**Auth:** `PRIVATE-TOKEN: {token}` header, token sourced from `GitLabSettings`

**Resolving `repo` to `project_id`:**

GitLab's pipeline API requires a numeric project ID. The provider must first resolve
`owner/name` to a project ID via:

`GET /api/v4/projects/{urllib.parse.quote("owner/name", safe="")}`

Cache this lookup for the lifetime of the provider instance.

**Key query params:**

- `per_page=100`
- `page=N` — iterate until `x-next-page` header is empty

**Status mapping:**

| GitLab `status` | `PipelineStatus` |
| --- | --- |
| `created` | `PENDING` |
| `waiting_for_resource` | `PENDING` |
| `preparing` | `PENDING` |
| `pending` | `PENDING` |
| `running` | `RUNNING` |
| `success` | `SUCCESS` |
| `failed` | `FAILURE` |
| `canceled` | `CANCELLED` |
| `skipped` | `SKIPPED` |
| `manual` | `UNKNOWN` |
| `scheduled` | `UNKNOWN` |
| anything else | `UNKNOWN` |

**Notes:**

- `pipeline.ref` → `branch`
- `pipeline.sha` → `commit_sha`
- `pipeline.web_url` → `url`
- `pipeline.id` (integer) → `str(pipeline["id"])` for the `id` field

---

## Deferred Providers

### Jenkins

- Requires per-installation base URL (env: `PIPE_PING_PROVIDER__JENKINS_BASE_URL`)
- Auth: username + API token via HTTP Basic
- Endpoint: `GET {base_url}/job/{job_name}/api/json?tree=builds[...]`
- Status mapping: `building=True` → `RUNNING`; `result: SUCCESS/FAILURE/ABORTED/NOT_BUILT`

### CircleCI

- Endpoint: `GET https://circleci.com/api/v2/project/gh/{owner}/{repo}/pipeline`
- Auth: `Circle-Token: {settings.provider.circleci_token}` header
- Pipelines and workflows are separate resources — may require two API calls per repo

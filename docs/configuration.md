# Configuration

## Where settings are read from

Pipe-Ping reads settings from these sources, in order of precedence:

1. Environment variables.
2. A `.env` file in the working directory.
3. The config file.

The config file and `.env` use the same format: one `NAME=value` per line, with
`#` for comments. See
[`.env.example`](https://github.com/EJEmmett/pipe-ping/blob/main/.env.example)
for a complete example.

To print the config file location, run `pipe-ping config-path`. The defaults
are:

| Platform | Config file |
| --- | --- |
| Linux | `~/.config/pipe-ping/config.env` |
| macOS | `~/Library/Application Support/pipe-ping/config.env` |
| Windows | `%LOCALAPPDATA%\pipe-ping\config.env` |

!!! note

    On Linux, Pipe-Ping follows the XDG base directory specification. Setting
    `$XDG_CONFIG_HOME`, `$XDG_DATA_HOME` or `$XDG_STATE_HOME` changes the
    config, database and log locations.

## GitHub

| Setting | Default | Description |
| --- | --- | --- |
| `PIPE_PING_GITHUB__TOKEN` | Required | A GitHub token that can read Actions on the monitored repositories |
| `PIPE_PING_GITHUB__REPOS` | Required | The repositories to monitor, as a JSON list |
| `PIPE_PING_GITHUB__API_URL` | `https://api.github.com` | The GitHub API URL. Change this to use GitHub Enterprise Server |
| `PIPE_PING_GITHUB__RUNS_PER_REPO` | `20` | The number of recent workflow runs to check in each repository |

For example, to monitor two repositories on GitHub Enterprise Server:

```env
PIPE_PING_GITHUB__TOKEN=github_pat_...
PIPE_PING_GITHUB__REPOS='["owner/repo", "owner/other-repo"]'
PIPE_PING_GITHUB__API_URL=https://github.example.com/api/v3
```

If the token or repositories are not set, Pipe-Ping skips the GitHub provider
and logs a warning. If no other provider is installed, Pipe-Ping exits.

## GitLab

| Setting | Default | Description |
| --- | --- | --- |
| `PIPE_PING_GITLAB__TOKEN` | Required | A GitLab token with the `read_api` scope on the monitored projects |
| `PIPE_PING_GITLAB__PROJECTS` | Required | The projects to monitor, by full path, as a JSON list |
| `PIPE_PING_GITLAB__API_URL` | `https://gitlab.com/api/v4` | The GitLab API URL. Change this to use a self-managed instance |
| `PIPE_PING_GITLAB__PIPELINES_PER_PROJECT` | `20` | The number of recent pipelines to check in each project |

For example, to monitor two projects on a self-managed GitLab instance:

```env
PIPE_PING_GITLAB__TOKEN=glpat-...
PIPE_PING_GITLAB__PROJECTS='["group/project", "group/subgroup/project"]'
PIPE_PING_GITLAB__API_URL=https://gitlab.example.com/api/v4
```

If the token or projects are not set, Pipe-Ping skips the GitLab provider and
logs a warning. You can configure GitHub, GitLab or both.

## Database

| Setting | Description |
| --- | --- |
| `PIPE_PING_SQLITE__PATH` | The location of the SQLite database |

| Platform | Default database |
| --- | --- |
| Linux | `~/.local/share/pipe-ping/pipe_ping.db` |
| macOS | `~/Library/Application Support/pipe-ping/pipe_ping.db` |
| Windows | `%LOCALAPPDATA%\pipe-ping\pipe_ping.db` |

## Logging

- Pipe-Ping writes every log message, including debug messages, to a JSON log
  file.
- The `-v` and `-vv` options only affect terminal output.
- The log file is rotated when it reaches its maximum size.

| Setting | Default | Description |
| --- | --- | --- |
| `PIPE_PING_STRUCTURED_LOGGING__PATH` | See below | The location of the log file |
| `PIPE_PING_STRUCTURED_LOGGING__MAX_BYTES` | `10485760` (10 MiB) | The size at which the log file is rotated |
| `PIPE_PING_STRUCTURED_LOGGING__BACKUP_COUNT` | `5` | The number of rotated log files to keep |

| Platform | Default log file |
| --- | --- |
| Linux | `~/.local/state/pipe-ping/log/pipe_ping.log` |
| macOS | `~/Library/Logs/pipe-ping/pipe_ping.log` |
| Windows | `%LOCALAPPDATA%\pipe-ping\Logs\pipe_ping.log` |

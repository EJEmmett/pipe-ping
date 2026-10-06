# Command line

| Command | Description |
| --- | --- |
| [`pipe-ping daemon`](#pipe-ping-daemon) | Monitor pipelines and send notifications |
| [`pipe-ping config-path`](#pipe-ping-config-path) | Print the config file location |
| [`pipe-ping list`](#pipe-ping-list) | List installed plugins |

## `pipe-ping daemon`

Monitor the configured repositories and send notifications. Runs until you
press ++ctrl+c++ or it receives a termination signal.

```bash
pipe-ping daemon [-v | -vv]
```

| Option | Description |
| --- | --- |
| `-v`, `--verbose` | Show info log messages in the terminal. Repeat (`-vv`) for debug messages |

Exits with status 1 if no provider, repository or notifier can be loaded.

## `pipe-ping config-path`

Print the config file location. The file does not need to exist.

```bash
pipe-ping config-path
```

## `pipe-ping list`

List the installed plugins of one kind, with each plugin's entry point name and
location.

```bash
pipe-ping list providers
pipe-ping list repository
pipe-ping list notifiers
```

Each subcommand accepts `-v` and `-vv`.

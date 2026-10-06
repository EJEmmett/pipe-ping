# Getting started

## Requirements

- Python 3.13 or later.
- A GitHub token that can read Actions on the repositories you want to monitor.
  For a fine-grained personal access token, grant **Actions: Read-only**.

## Install

=== "uv"

    ```bash
    uv tool install pipe-ping
    ```

=== "pipx"

    ```bash
    pipx install pipe-ping
    ```

## Configuration
### Environment variables

Environment variables take precedence over a config file.

=== "Bash"

    ```bash
    export PIPE_PING_GITHUB__TOKEN=github_pat_...
    export PIPE_PING_GITHUB__REPOS='["owner/repo", "owner/other-repo"]'
    pipe-ping daemon
    ```

=== "PowerShell"

    ```powershell
    $env:PIPE_PING_GITHUB__TOKEN = "github_pat_..."
    $env:PIPE_PING_GITHUB__REPOS = '["owner/repo", "owner/other-repo"]'
    pipe-ping daemon
    ```

### Configuration file

1. Print the location of the config file:

    ```bash
    pipe-ping config-path
    ```

2. Create the file and add your token and the repositories to monitor:

    ```env
    PIPE_PING_GITHUB__TOKEN=github_pat_...
    PIPE_PING_GITHUB__REPOS='["owner/repo", "owner/other-repo"]'
    ```

For other settings, see [Configuration](configuration.md).

## Run

```bash
pipe-ping daemon
```

Pipe-Ping prints each status change to the terminal and shows a desktop
notification when a pipeline run finishes. Press ++ctrl+c++ to stop it.

To show log messages in the terminal, add `-v` for info or `-vv` for debug:

```bash
pipe-ping daemon -v
```

To keep Pipe-Ping running after you close the terminal, see
[Running in the background](running-in-the-background.md).

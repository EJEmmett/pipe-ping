# Pipe-Ping

Pipe-Ping monitors your CI/CD pipelines and notifies you when they succeed,
fail or are cancelled.

- Supports GitHub Actions, including GitHub Enterprise Server.
- Notifies you in the terminal and with desktop notifications on Linux, macOS
  and Windows.
- Reports only status changes. Pipelines that finish while Pipe-Ping is stopped
  are reported when it next starts.
- Runs in the background as a systemd service, launchd agent or Windows
  scheduled task.
- Supports plugins for other CI/CD services, notification channels and storage
  backends.

**Documentation:** <https://ejemmett.github.io/pipe-ping/>

## Quick start

Pipe-Ping requires Python 3.13 or later and a GitHub token with read access to
Actions on the repositories you want to monitor.

Install Pipe-Ping with [uv](https://docs.astral.sh/uv/) or
[pipx](https://pipx.pypa.io/):

```bash
uv tool install pipe-ping
```

Print the location of the config file:

```bash
pipe-ping config-path
```

Create the file and add your token and the repositories to monitor:

```env
PIPE_PING_GITHUB__TOKEN=github_pat_...
PIPE_PING_GITHUB__REPOS='["owner/repo", "owner/other-repo"]'
```

Then start Pipe-Ping:

```bash
pipe-ping daemon
```

## Learn more

- [Getting started](https://ejemmett.github.io/pipe-ping/getting-started/)
- [Configuration](https://ejemmett.github.io/pipe-ping/configuration/)
- [Notifications](https://ejemmett.github.io/pipe-ping/notifications/)
- [Running in the background](https://ejemmett.github.io/pipe-ping/running-in-the-background/)
- [Writing a plugin](https://ejemmett.github.io/pipe-ping/plugins/)
- [Development](https://ejemmett.github.io/pipe-ping/development/)

## License

MIT

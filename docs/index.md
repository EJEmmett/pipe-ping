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

## Next steps

- [Getting started](getting-started.md): install Pipe-Ping and monitor your
  first repository.
- [Configuration](configuration.md): every available setting.
- [Writing a plugin](plugins/index.md): add a CI/CD service or notification
  channel.

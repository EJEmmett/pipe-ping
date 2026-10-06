# Notifications

Pipe-Ping includes two notifiers, both enabled by default.

## Terminal

Every status change is printed to the terminal, including when a pipeline run
is queued or starts. Each line shows the status, repository, branch, short
commit SHA and a link to the pipeline run:

```text
✓ success    owner/repo  main  3f2a9c1  https://github.com/owner/repo/actions/runs/1234
```

## Desktop

- A notification is shown when a pipeline run succeeds, fails or is cancelled.
- Failures are shown with critical urgency.
- Clicking a notification opens the pipeline run in your browser, except on
  macOS.

Desktop notifications need a notification service:

| Platform | Requirement |
| --- | --- |
| Linux | A desktop with a notification service, such as GNOME or KDE |
| Windows | None |
| macOS | Pipe-Ping must run as an app bundle. See [Running in the background](running-in-the-background.md#macos-launchd) |

Without a notification service, such as on a headless server or in WSL,
Pipe-Ping logs a warning at startup and uses terminal output only.

### Permissions

The first time Pipe-Ping starts, your system may ask whether to allow its
notifications. If you block them, enable them for Pipe-Ping in your system
settings, then restart Pipe-Ping.

# Running in the background

The [`examples`](https://github.com/EJEmmett/pipe-ping/tree/main/examples)
directory contains the files for each platform. Before you start:

1. Clone the repository and run the commands below from its root.
2. Install Pipe-Ping with `uv tool install pipe-ping`.
3. Create the config file. See [Getting started](getting-started.md#configuration-file).

## Linux (systemd)

Install and start the systemd user service:

```bash
mkdir -p ~/.config/systemd/user
cp examples/linux/pipe-ping.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now pipe-ping
```

Check its status and output:

```bash
systemctl --user status pipe-ping
journalctl --user -u pipe-ping
```

The service runs `~/.local/bin/pipe-ping`. If `pipe-ping` is installed
elsewhere, set `ExecStart` in `pipe-ping.service` to the output of
`which pipe-ping`.

## macOS (launchd)

macOS only shows notifications from signed app bundles, so Pipe-Ping must be
built as an app.

1. Build `Pipe-Ping.app` and copy it to `/Applications`:

    ```bash
    examples/macos/build_app.sh
    cp -R examples/macos/dist/Pipe-Ping.app /Applications/
    ```

2. Register a launch agent to start it at login:

    ```bash
    cp examples/macos/io.github.ejemmett.pipe-ping.plist ~/Library/LaunchAgents/
    launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/io.github.ejemmett.pipe-ping.plist
    ```

3. Allow notifications when macOS asks.

To stop the agent:

```bash
launchctl bootout gui/$(id -u)/io.github.ejemmett.pipe-ping
```

### Including plugins

Plugins must be built into the app. For each plugin, edit the command in
`examples/macos/build_app.sh`:

1. Add `--with <path>` to the `uv run` options.
2. Add `--copy-metadata <distribution name>`.
3. Add `--collect-submodules <module name>`.

For example, to include the example plugin (added lines are highlighted):

```bash hl_lines="1 7 9"
uv run --project ../.. --with pyinstaller --with ../plugin pyinstaller \
    --windowed \
    --noconfirm \
    --name Pipe-Ping \
    --osx-bundle-identifier io.github.ejemmett.pipe-ping \
    --copy-metadata pipe-ping \
    --copy-metadata pipe-ping-example \
    --collect-submodules pipe_ping \
    --collect-submodules pipe_ping_example \
    --collect-data pipe_ping \
    --collect-data desktop_notifier \
    launcher.py
```

Paths are relative to `examples/macos`, because the script runs from there.
Rebuild and reinstall the app after editing the script.

## Windows (Task Scheduler)

Register a scheduled task that starts Pipe-Ping in the background now and at
each login:

```powershell
.\examples\windows\install.ps1
```

To remove the task:

```powershell
.\examples\windows\uninstall.ps1
```

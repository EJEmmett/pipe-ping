# Pipe-Ping

Pipe-Ping keeps an eye on your GitHub Actions and lets you know when a
workflow run passes, fails or gets cancelled, so you don't have to keep a
browser tab open.

It checks your repositories every minute and only tells you about runs that
actually changed. If something finished while it wasn't running, you'll hear
about it the next time you start it.

## Getting started

You'll need Python 3.13 or newer, [uv](https://docs.astral.sh/uv/), and a
GitHub token that can read Actions on the repositories you want to watch.

```bash
git clone https://github.com/EJEmmett/pipe-ping.git
cd pipe-ping
make install
```

Copy the example config and fill in your token and repositories:

```bash
cp .env.example .env
```

Then run it:

```bash
uv run pipe-ping daemon
```

Use `-v` or `-vv` if you want to see what it's doing.

## Notifications

Every change is printed to the terminal. On desktops that support it, you'll
also get a notification when a run finishes, and clicking it opens the run on
GitHub. If desktop notifications aren't available, for example on a server or
in WSL, Pipe-Ping just sticks to the terminal.

## Configuration

Settings can go in `.env` or be set as environment variables. Besides the token
and repository list, you can point Pipe-Ping at a GitHub Enterprise server,
change how many recent runs it looks at, or move its database and log files.
`.env.example` lists everything you can set.

## Extending

Where runs come from, where they're stored and how you're notified are all
plugins, so other packages can add new ones. `pipe-ping list` shows what's
installed.

## Development

```bash
make install   # install dependencies
make test      # run the tests on every supported Python version
make lint      # check style and types
make format    # fix style
make clean     # remove build output and caches
```

The desktop notification tests need `dbus-daemon` and are skipped without it.

## License

MIT

# Development

## Set up

Clone the repository and install the development dependencies:

```bash
git clone https://github.com/EJEmmett/pipe-ping.git
cd pipe-ping
make install
```

To run your local copy, create a `.env` file in the project directory, then
run:

```bash
uv run pipe-ping daemon
```

## Common tasks

| Command | Description |
| --- | --- |
| `make test` | Run the tests on Python 3.13 and 3.14 |
| `make lint` | Check linting, formatting and types |
| `make format` | Fix lint errors and format the code |
| `make docs` | Serve the documentation at <http://localhost:8000> with live reload |
| `make docs-build` | Build the documentation into `site/` |
| `make clean` | Remove build artifacts and caches |

To pass arguments to pytest, run nox directly:

```bash
uv run nox -- -k github
```

The desktop notification integration tests need `dbus-daemon`. They are
skipped if it is not installed.

## Documentation

- The documentation is built with [Zensical](https://zensical.org/) from the
  Markdown files in `docs/`.
- The [API reference](reference/api.md) is generated from docstrings by
  [mkdocstrings](https://mkdocstrings.github.io/). When you change the public
  models or plugin protocols, update their docstrings.
- The documentation is published to GitHub Pages on every push to `main`.

## Releasing

1. Bump the version with `make bump-patch`, `make bump-minor` or
   `make bump-major`, then commit the change.
2. Run `make release` to run the linters and tests, then tag the commit and
   push the tag.
3. The tag starts the release workflow, which publishes the package to PyPI and
   creates a GitHub release.

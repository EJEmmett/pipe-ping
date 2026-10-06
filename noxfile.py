import nox

nox.options.default_venv_backend = "uv"
nox.options.sessions = ["tests"]
nox.options.reuse_venv = "yes"

PYTHON_VERSIONS = ["3.13", "3.14"]


def sync_locked_dependencies(session: nox.Session) -> None:
    """Install the project and dev group from ``uv.lock`` into the session venv."""
    session.run_install(
        "uv",
        "sync",
        "--locked",
        f"--python={session.virtualenv.location}",
        env={"UV_PROJECT_ENVIRONMENT": session.virtualenv.location},
        silent=True,
    )


@nox.session(python=PYTHON_VERSIONS)
def tests(session: nox.Session) -> None:
    """Run the test suite. Extra arguments are passed to pytest."""
    sync_locked_dependencies(session)
    session.run("pytest", "-rs", *session.posargs)

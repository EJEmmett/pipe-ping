set windows-shell := ["cmd.exe", "/c"]
set shell := ["sh", "-c"]

default: test lint

install:
    uv sync

dev: mongo
    uv run pipe-ping watch

test:
    uv run pytest

lint:
    uv run ruff check .
    uv run ruff format --check .
    uv run ty check

format:
    uv run ruff check --fix .
    uv run ruff format .

mongo:
    podman-compose up -d

clean:
    podman-compose down
    {{ if os() == "windows" { \
        'for /d /r . %%d in (__pycache__ .pytest_cache .ruff_cache) do @if exist "%%d" rd /s /q "%%d"' \
    } else { \
        'find . -type d \( -name __pycache__ -o -name .pytest_cache -o -name .ruff_cache \) -exec rm -rf {} +' \
    } }}

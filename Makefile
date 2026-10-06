.PHONY: default install test lint format clean

default: test lint

install:
	uv sync

test:
	uv run nox

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run ty check

format:
	uv run ruff check --fix .
	uv run ruff format .

clean:
	rm -rf dist build *.egg-info .nox .pytest_cache .ruff_cache .ty_cache .mypy_cache htmlcov .coverage coverage.xml
	find . -path ./.venv -prune -o -type d -name __pycache__ -exec rm -rf {} +

VERSION = $(shell uv version --short)

.PHONY: default install test lint format docs docs-build clean build bump-patch bump-minor bump-major tag release

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

docs:
	uv run --group docs zensical serve

docs-build:
	uv run --group docs zensical build --clean --strict

clean:
	rm -rf dist build site .cache *.egg-info .nox .pytest_cache .ruff_cache .ty_cache .mypy_cache htmlcov .coverage coverage.xml
	find . -path ./.venv -prune -o -type d -name __pycache__ -exec rm -rf {} +

build:
	rm -rf dist
	uv build

bump-patch:
	uv version --bump patch

bump-minor:
	uv version --bump minor

bump-major:
	uv version --bump major

tag:
	@git diff --quiet HEAD || { echo "Commit your changes before tagging."; exit 1; }
	git tag -a v$(VERSION) -m "Release v$(VERSION)"
	git push origin v$(VERSION)

release: lint test tag

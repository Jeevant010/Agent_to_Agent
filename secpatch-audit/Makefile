.PHONY: install test lint format

install:
	uv sync --all-extras

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run mypy src

format:
	uv run ruff format .
	uv run ruff check --fix .

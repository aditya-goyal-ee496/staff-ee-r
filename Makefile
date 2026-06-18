.DEFAULT_GOAL := help
.PHONY: help install test eval lint format match clean

ROLE ?= backend engineer with database experience

help:  ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-12s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies into the project venv (uv sync)
	uv sync

test:  ## Run unit + integration tests
	uv run pytest

eval:  ## Run deterministic scenario evals (Promptfoo + DeepEval relevance suites land later)
	uv run pytest evals

lint:  ## Check formatting, lint, and types
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy src

format:  ## Auto-format and apply safe lint fixes
	uv run ruff format .
	uv run ruff check --fix .

match:  ## Run the matcher for a role, e.g. make match ROLE="backend engineer"
	uv run staffeer match "$(ROLE)"

clean:  ## Remove caches and build artifacts
	rm -rf .pytest_cache .ruff_cache .mypy_cache **/__pycache__

.DEFAULT_GOAL := help
.PHONY: help install test eval lint format match match-text index arch clean

ROLE ?= backend engineer with database experience

help:  ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-12s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies (llm + nlp + semantic + parse extras) into the project venv
	# llm (DSPy reasoner) + nlp (Presidio PII scrubber) + semantic (Milvus Lite +
	# sentence-transformers for `match --semantic`) + parse (Docling profile parser) so
	# the full CLI works out of the box. Add eval as needed.
	uv sync --extra llm --extra nlp --extra semantic --extra parse
	# Presidio's NER engine requires the spaCy en_core_web_sm model
	uv run python -m spacy download en_core_web_sm

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

match:  ## Match a role by id, e.g. make match ROLE="ROLE-01"
	uv run staffeer match "$(ROLE)"

match-text:  ## Match a free-text role, e.g. make match-text ROLE="backend engineer with database experience" (needs OPENROUTER_API_KEY in .env)
	uv run staffeer match-text "$(ROLE)"

index:  ## (Re)build semantic index embeddings; requires STAFFEER_MILVUS_PATH in .env
	uv run staffeer index

arch:  ## Build + serve the LikeC4 diagram viewer (requires Node; build then preview)
	# Uses `build` + `preview` (production bundle) instead of `start`: the dev server's
	# rolldown-vite transform pipeline throws "SyntaxError: Unexpected token '('" on this
	# toolchain (reproduced on likec4 1.56 + 1.58), leaving a blank page. `preview` only
	# serves a prior production build, so `build` (into dist/) must run first; it then
	# prints a clickable localhost URL.
	npx likec4 build
	npx likec4 preview

clean:  ## Remove caches and build artifacts
	rm -rf .pytest_cache .ruff_cache .mypy_cache **/__pycache__

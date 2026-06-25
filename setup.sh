#!/usr/bin/env bash
#
# Bootstrap Staffeer on a fresh machine.
#
#   - Installs whatever is missing: uv (required), mise (optional toolchain),
#     and a uv-managed Python 3.12 (matches .python-version / .mise.toml).
#   - Syncs project dependencies (incl. the llm + nlp extras + spaCy model) so the
#     full CLI — including free-text `match-text` — works out of the box.
#   - Seeds .env from .env.example for the OPENROUTER_API_KEY used by `match-text`.
#   - Installs the `staffeer` CLI on your PATH so you can run it directly.
#
# Idempotent: re-running only fills in what is missing. Usage:
#   ./setup.sh            # full bootstrap + global CLI install
#   ./setup.sh --no-cli   # bootstrap deps only (use `uv run staffeer` instead)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

INSTALL_CLI=1
[[ "${1:-}" = "--no-cli" ]] && INSTALL_CLI=0

# Ensure user-local bin dirs are visible for tools installed below.
export PATH="${HOME}/.local/bin:${PATH}"

log() { printf '\033[36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[33mwarn:\033[0m %s\n' "$*" >&2; }
die() {
  printf '\033[31merror:\033[0m %s\n' "$*" >&2
  exit 1
}
have() { command -v "$1" >/dev/null 2>&1; }

# 1. uv — package manager and venv (required).
if have uv
then
  log "uv present: $(uv --version)"
else
  log "Installing uv ..."
  if have curl
  then
    curl -LsSf https://astral.sh/uv/install.sh | sh
  elif have wget
  then
    wget -qO- https://astral.sh/uv/install.sh | sh
  else
    die "need curl or wget to install uv; install one and re-run."
  fi
  have uv || die "uv install finished but uv is not on PATH; restart your shell and re-run."
fi

# 2. mise — toolchain manager from the documented stack (optional; best-effort).
#    uv provisions Python below regardless, so a mise failure is non-fatal.
if have mise
then
  log "mise present: $(mise --version 2>/dev/null || echo unknown)"
  mise install 2>/dev/null || warn "mise install skipped (continuing; uv manages Python)."
else
  log "Installing mise (optional toolchain manager) ..."
  if have curl && curl -fsSL https://mise.run | sh
  then
    have mise && mise install 2>/dev/null || true
  else
    warn "mise not installed (optional) — uv will manage Python instead."
  fi
fi

# 3. Python 3.12 — managed by uv so the CLI runs without touching system Python.
log "Ensuring Python 3.12 is available (uv-managed) ..."
uv python install 3.12

# 4. Dependencies — creates .venv and installs the project (editable) + dev tools.
#    Includes the llm + nlp extras so the full CLI works out of the box: free-text
#    `match-text` needs the DSPy reasoner (llm) and the fail-closed Presidio PII
#    scrubber (nlp). Remaining heavy extras stay out until needed: `uv sync --extra parse`.
log "Syncing dependencies (uv sync --extra llm --extra nlp) ..."
uv sync --extra llm --extra nlp

# 4b. spaCy model — Presidio's NER engine needs en_core_web_sm to scrub PII before any LLM call.
log "Downloading the spaCy model for PII scrubbing (en_core_web_sm) ..."
uv run python -m spacy download en_core_web_sm

# 4c. .env — seed from the example so OPENROUTER_API_KEY (used by `match-text`) is easy to set.
#     Never overwrites an existing .env; the key stays blank until you fill it in.
if [[ ! -f .env ]] && [[ -f .env.example ]]
then
  log "Creating .env from .env.example (set OPENROUTER_API_KEY for free-text matching) ..."
  cp .env.example .env
fi

# 5. Install the CLI on PATH so `staffeer` is runnable from anywhere.
#    `uv tool install` builds an ISOLATED environment — it does NOT inherit the .venv
#    above — so the llm + nlp extras and the spaCy model must be requested here too,
#    or the global `staffeer match-text` fails with ModuleNotFoundError (presidio/dspy).
#    The model wheel is pinned because the tool env can't run `spacy download` after install.
SPACY_MODEL_WHL="https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl"
if [[ "${INSTALL_CLI}" -eq 1 ]]
then
  log "Installing the staffeer CLI on your PATH (uv tool install, with llm+nlp extras) ..."
  uv tool install --force --editable ".[llm,nlp]" --with "en_core_web_sm @ ${SPACY_MODEL_WHL}"
  uv tool update-shell 2>/dev/null || true
fi

# 6. Verify.
log "Verifying installation ..."
uv run staffeer --help >/dev/null && log "CLI runs via 'uv run staffeer'."
if [[ "${INSTALL_CLI}" -eq 1 ]]
then
  if have staffeer
  then
    log "CLI on PATH: $(command -v staffeer)"
  else
    warn "staffeer is installed but not on PATH yet — restart your shell, or use 'uv run staffeer'."
  fi
fi

cat <<'DONE'

Staffeer is ready. Next steps:
  staffeer --help                       # explore commands (or: uv run staffeer --help)
  make test                             # run the test suite
  make lint                             # ruff + mypy
  make eval                             # deterministic scenario evals

Run the matcher (defaults to planning/raw-data/demand-supply.xlsx; override with $STAFFEER_DATA):
  staffeer roles                        # list open roles
  make match ROLE="ROLE-01"             # ranked beach shortlist for a role (by id)

Match a free-text role (LLM-backed; set OPENROUTER_API_KEY in .env first):
  make match-text ROLE="backend engineer with database experience"

Remaining optional extras (not needed for the CLI above):
  uv sync --extra parse --extra eval    # docling profile parsing / DeepEval suites
DONE

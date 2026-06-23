#!/usr/bin/env bash
#
# Bootstrap Staffeer on a fresh machine.
#
#   - Installs whatever is missing: uv (required), mise (optional toolchain),
#     and a uv-managed Python 3.12 (matches .python-version / .mise.toml).
#   - Syncs project dependencies into the project venv (uv sync).
#   - Installs the `staffeer` CLI on your PATH so you can run it directly.
#
# Idempotent: re-running only fills in what is missing. Usage:
#   ./setup.sh            # full bootstrap + global CLI install
#   ./setup.sh --no-cli   # bootstrap deps only (use `uv run staffeer` instead)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

INSTALL_CLI=1
[ "${1:-}" = "--no-cli" ] && INSTALL_CLI=0

# Ensure user-local bin dirs are visible for tools installed below.
export PATH="$HOME/.local/bin:$PATH"

log()  { printf '\033[36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[33mwarn:\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[31merror:\033[0m %s\n' "$*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

# 1. uv — package manager and venv (required).
if have uv; then
    log "uv present: $(uv --version)"
else
    log "Installing uv ..."
    if have curl; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    elif have wget; then
        wget -qO- https://astral.sh/uv/install.sh | sh
    else
        die "need curl or wget to install uv; install one and re-run."
    fi
    have uv || die "uv install finished but uv is not on PATH; restart your shell and re-run."
fi

# 2. mise — toolchain manager from the documented stack (optional; best-effort).
#    uv provisions Python below regardless, so a mise failure is non-fatal.
if have mise; then
    log "mise present: $(mise --version 2>/dev/null || echo unknown)"
    mise install 2>/dev/null || warn "mise install skipped (continuing; uv manages Python)."
else
    log "Installing mise (optional toolchain manager) ..."
    if have curl && curl -fsSL https://mise.run | sh; then
        have mise && mise install 2>/dev/null || true
    else
        warn "mise not installed (optional) — uv will manage Python instead."
    fi
fi

# 3. Python 3.12 — managed by uv so the CLI runs without touching system Python.
log "Ensuring Python 3.12 is available (uv-managed) ..."
uv python install 3.12

# 4. Dependencies — creates .venv and installs the project (editable) + dev tools.
#    Heavy extras (llm/nlp/parse/eval) stay out until their slices need them; add with
#    e.g. `uv sync --extra nlp --extra parse`.
log "Syncing dependencies (uv sync) ..."
uv sync

# 5. Install the CLI on PATH so `staffeer` is runnable from anywhere.
if [ "$INSTALL_CLI" -eq 1 ]; then
    log "Installing the staffeer CLI on your PATH (uv tool install) ..."
    uv tool install --force --editable .
    uv tool update-shell 2>/dev/null || true
fi

# 6. Verify.
log "Verifying installation ..."
uv run staffeer --help >/dev/null && log "CLI runs via 'uv run staffeer'."
if [ "$INSTALL_CLI" -eq 1 ]; then
    if have staffeer; then
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

Run the matcher (needs the workbook in planning/raw-data, or set $STAFFEER_DATA):
  staffeer roles                        # list open roles
  make match ROLE="ROLE-01"             # ranked beach shortlist for a role

Optional extras (installed per slice as needed):
  uv sync --extra nlp --extra parse --extra llm --extra eval
DONE

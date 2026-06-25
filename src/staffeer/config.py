"""Application configuration loaded from the environment (12-factor).

No secrets live in code; values come from the process environment (see `.env.example`).
`Settings` carries raw env secrets; `StaffeerConfig` is the frozen config `build_matcher`
consumes — it adds the capability selectors and per-contributor weights that pick a real-vs-null
adapter per port (`docs/tasks/parallelization-guide.md`). Capabilities default off, so the
out-of-the-box wiring is the inert, all-null matcher.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field

from staffeer.domain.models import SupplyState

# Repo root is three levels up from this file (src/staffeer/config.py).
_REPO_ROOT = Path(__file__).resolve().parents[2]
# The demand-supply workbook bundled under planning/raw-data, used when $STAFFEER_DATA is unset.
DEFAULT_DATA_FILE = _REPO_ROOT / "planning" / "raw-data" / "demand-supply.xlsx"
# The local dotenv loaded for developer convenience by the CLI entry point.
DEFAULT_ENV_FILE = _REPO_ROOT / ".env"


def load_env_file(path: Path | None = None) -> None:
    """Load `key=value` pairs from a local `.env` into the process environment.

    A developer convenience so `STAFFEER_DATA`/`OPENROUTER_API_KEY` set in `.env` are honoured.
    Real environment variables always win (`override=False`, preserving 12-factor precedence);
    a missing file is a no-op.
    """
    load_dotenv(path or DEFAULT_ENV_FILE, override=False)


def _resolve_data_path() -> str | None:
    """The workbook path from `$STAFFEER_DATA`, else the bundled raw-data workbook if present."""
    configured = os.environ.get("STAFFEER_DATA")
    if configured:
        return configured
    return str(DEFAULT_DATA_FILE) if DEFAULT_DATA_FILE.is_file() else None


class Settings(BaseModel):
    """Immutable runtime settings sourced from environment variables."""

    model_config = ConfigDict(frozen=True)

    data_path: str | None = None
    openrouter_api_key: str | None = None

    @classmethod
    def from_env(cls) -> Settings:
        """Build settings from the current process environment."""
        return cls(
            data_path=_resolve_data_path(),
            openrouter_api_key=os.environ.get("OPENROUTER_API_KEY"),
        )


class StaffeerConfig(BaseModel):
    """Frozen configuration that selects which adapters `build_matcher` wires.

    Capability selectors stay `False` by default (null objects); a track flips one on once
    its real adapter is wired. `weights` tunes the per-contributor blend without code changes
    (Principle 4). An LLM/semantic path with no real PII scrubber makes `build_matcher` raise.
    """

    model_config = ConfigDict(frozen=True)

    data_path: str | None = None
    openrouter_api_key: str | None = None
    semantic_enabled: bool = False
    llm_enabled: bool = False
    profiles_enabled: bool = False
    feedback_dir: str | None = None
    include_states: tuple[SupplyState, ...] = (SupplyState.BEACH,)
    weights: dict[str, float] = Field(default_factory=dict)
    milvus_path: str | None = None
    embedding_model: str = "all-MiniLM-L6-v2"

    @classmethod
    def from_env(cls) -> StaffeerConfig:
        """Build config from env secrets, leaving capabilities at their defaults."""
        settings = Settings.from_env()
        profiles_enabled_str = os.environ.get("STAFFEER_PROFILES", "")
        profiles_enabled = profiles_enabled_str.strip().lower() in ("1", "true", "yes")
        return cls(
            data_path=settings.data_path,
            openrouter_api_key=settings.openrouter_api_key,
            profiles_enabled=profiles_enabled,
            feedback_dir=os.environ.get("STAFFEER_FEEDBACK_DIR"),
            milvus_path=os.environ.get("STAFFEER_MILVUS_PATH"),
            embedding_model=os.environ.get("STAFFEER_EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
        )

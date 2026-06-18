"""Application configuration loaded from the environment (12-factor).

No secrets live in code; values come from the process environment (see `.env.example`).
`Settings` carries raw env secrets; `StaffeerConfig` is the frozen config `build_matcher`
consumes — it adds the capability selectors and per-contributor weights that pick a real-vs-null
adapter per port (`docs/tasks/parallelization-guide.md`). Capabilities default off, so the
out-of-the-box wiring is the inert, all-null matcher.
"""

from __future__ import annotations

import os

from pydantic import BaseModel, ConfigDict, Field

from staffeer.domain.models import SupplyState


class Settings(BaseModel):
    """Immutable runtime settings sourced from environment variables."""

    model_config = ConfigDict(frozen=True)

    data_path: str | None = None
    openrouter_api_key: str | None = None

    @classmethod
    def from_env(cls) -> Settings:
        """Build settings from the current process environment."""
        return cls(
            data_path=os.environ.get("STAFFEER_DATA"),
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
    include_states: tuple[SupplyState, ...] = (SupplyState.BEACH,)
    weights: dict[str, float] = Field(default_factory=dict)

    @classmethod
    def from_env(cls) -> StaffeerConfig:
        """Build config from env secrets, leaving capabilities at their defaults."""
        settings = Settings.from_env()
        return cls(
            data_path=settings.data_path,
            openrouter_api_key=settings.openrouter_api_key,
        )

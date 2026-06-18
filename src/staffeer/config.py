"""Application configuration loaded from the environment (12-factor).

No secrets live in code; values come from the process environment (see `.env.example`).
This is the seed of the frozen `StaffeerConfig` that C1 (`docs/tasks/00b-contracts.md`)
extends with capability selectors and per-contributor weights.
"""

from __future__ import annotations

import os

from pydantic import BaseModel, ConfigDict


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

"""Domain error hierarchy.

Errors are defined in the core; adapters map infrastructure failures (bad xlsx, corrupt
PDF, PII-engine failure) onto these at the boundary, so the domain never sees an
infrastructure exception (`docs/rules/hexagonal-architecture.md`, `docs/rules/code-quality.md`).
"""

from __future__ import annotations


class StaffeerError(Exception):
    """Base class for every error the domain raises or an adapter maps onto."""


class SupplyDemandError(StaffeerError):
    """Supply/demand data could not be loaded, or a requested role does not exist."""


class ProfileParseError(StaffeerError):
    """A consultant profile could not be parsed into a `ParsedProfile`."""


class FeedbackError(StaffeerError):
    """Consultant feedback could not be loaded."""


class PIIScrubbingError(StaffeerError):
    """The PII scrubber failed; text must not reach an LLM unscrubbed (fail closed)."""

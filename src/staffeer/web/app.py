"""FastAPI web adapter — exposes the Staffeer matcher over HTTP.

Three endpoints mirror the CLI commands:
  GET  /api/roles          — list open roles
  POST /api/match          — match by role ID
  POST /api/match-text     — match from free-text description

The static single-page UI is served from `static/index.html`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from staffeer.composition import build_matcher, build_role_parser
from staffeer.config import StaffeerConfig, load_env_file
from staffeer.domain.errors import StaffeerError, SupplyDemandError
from staffeer.domain.models import EligibilityResult, Match, Shortlist, SupplyState
from staffeer.ports.reasoner import LLMReasonerError

_STATIC_DIR = Path(__file__).parent / "static"

load_env_file()

app = FastAPI(title="Staffeer", description="Ranked, explainable consultant shortlists.")

app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class MatchRequest(BaseModel):
    role_id: str
    show_excluded: bool = False
    semantic: bool = False
    include: list[str] = Field(default_factory=list)


class MatchTextRequest(BaseModel):
    query: str
    show_excluded: bool = False
    semantic: bool = False


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------


def _serialise_match(position: int, match: Match) -> dict[str, Any]:
    c = match.consultant
    return {
        "rank": position,
        "id": c.id,
        "name": c.name,
        "grade": c.grade,
        "location": c.location,
        "state": c.state.value,
        "available_from": c.available_from.isoformat() if c.available_from else None,
        "score": round(match.score, 4),
        "contributions": [
            {
                "source": sc.source,
                "value": round(sc.value, 4),
                "weight": sc.weight,
                "weighted": round(sc.weighted, 4),
                "detail": sc.detail,
            }
            for sc in match.contributions
        ],
        "explanation": [
            {"source": f.source, "summary": f.summary, "detail": f.detail}
            for f in match.explanation.factors
        ],
    }


def _serialise_excluded(result: EligibilityResult) -> dict[str, Any]:
    c = result.consultant
    return {
        "id": c.id,
        "name": c.name,
        "location": c.location,
        "reasons": [{"name": f.name, "reason": f.reason} for f in result.failures],
    }


def _serialise_shortlist(shortlist: Shortlist, show_excluded: bool) -> dict[str, Any]:
    return {
        "role": {
            "id": shortlist.role.id,
            "title": shortlist.role.title,
            "location": shortlist.role.location,
            "priority": shortlist.role.priority.value,
        },
        "matches": [_serialise_match(i + 1, m) for i, m in enumerate(shortlist.matches)],
        "excluded": [_serialise_excluded(r) for r in shortlist.excluded] if show_excluded else [],
    }


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------


def _make_config(semantic: bool = False, include: list[str] | None = None) -> StaffeerConfig:
    config = StaffeerConfig.from_env()
    if semantic:
        if not config.milvus_path:
            raise HTTPException(
                status_code=422,
                detail="STAFFEER_MILVUS_PATH is required to enable semantic matching.",
            )
        config = config.model_copy(update={"semantic_enabled": True})
    if include:
        states: set[SupplyState] = set(config.include_states)
        for token in include:
            for part in token.split(","):
                part = part.strip()
                if not part:
                    continue
                try:
                    states.add(SupplyState(part))
                except ValueError:
                    raise HTTPException(
                        status_code=422, detail=f"Unknown supply state: '{part}'"
                    ) from None
        config = config.model_copy(update={"include_states": tuple(states)})
    return config


def _make_llm_config(semantic: bool = False) -> StaffeerConfig:
    config = _make_config(semantic)
    if not config.openrouter_api_key:
        raise HTTPException(
            status_code=422,
            detail="OPENROUTER_API_KEY is required for free-text matching.",
        )
    return config.model_copy(update={"llm_enabled": True})


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/")  # type: ignore[untyped-decorator]
def index() -> FileResponse:
    return FileResponse(_STATIC_DIR / "index.html")


@app.get("/api/roles")  # type: ignore[untyped-decorator]
def list_roles() -> list[dict[str, Any]]:
    """Return all open roles from the workbook."""
    try:
        matcher = build_matcher(StaffeerConfig.from_env())
    except StaffeerError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return [
        {
            "id": r.id,
            "title": r.title,
            "location": r.location,
            "priority": r.priority.value,
            "required_skills": list(r.required_skills),
            "start_date": r.start_date.isoformat() if r.start_date else None,
            "co_location": r.co_location,
        }
        for r in matcher.supply.open_roles()
    ]


@app.post("/api/match")  # type: ignore[untyped-decorator]
def match_role(req: MatchRequest) -> dict[str, Any]:
    """Match a role by ID and return the ranked shortlist."""
    try:
        config = _make_config(req.semantic, req.include)
        matcher = build_matcher(config)
        role = matcher.supply.role(req.role_id)
    except HTTPException:
        raise
    except SupplyDemandError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except StaffeerError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    shortlist = matcher.match(role)
    return _serialise_shortlist(shortlist, req.show_excluded)


@app.post("/api/match-text")  # type: ignore[untyped-decorator]
def match_text(req: MatchTextRequest) -> dict[str, Any]:
    """Parse a free-text role description and return the ranked shortlist."""
    try:
        config = _make_llm_config(req.semantic)
        matcher = build_matcher(config)
        role_parser = build_role_parser(config)
        role = role_parser.parse(req.query)
    except HTTPException:
        raise
    except (ValueError, LLMReasonerError) as exc:
        raise HTTPException(
            status_code=422, detail=f"Could not parse role description: {exc}"
        ) from exc
    except StaffeerError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    shortlist = matcher.match(role)
    return _serialise_shortlist(shortlist, req.show_excluded)

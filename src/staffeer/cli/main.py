"""Typer CLI — the driving adapter for the matcher (I1, `docs/tasks/02-beach-matching.md`).

Two commands: `roles` lists the open roles in the workbook, and `match ROLE_ID` prints the
ranked, explained beach shortlist for one role (with `--show-excluded` to see why others were
dropped). The CLI only presents; all wiring goes through `build_matcher` and `build_role_parser`,
never adapters directly (`docs/tasks/parallelization-guide.md`).
"""

from __future__ import annotations

import typer

from staffeer.composition import build_matcher, build_role_parser
from staffeer.config import StaffeerConfig, load_env_file
from staffeer.domain.errors import StaffeerError, SupplyDemandError
from staffeer.domain.explain import SKILLS_SOURCE
from staffeer.domain.matcher import Matcher, _build_consultant_summary
from staffeer.domain.models import Consultant, EligibilityResult, Match, Shortlist
from staffeer.ports.reasoner import LLMReasonerError
from staffeer.ports.semantic_index import IndexItem

app = typer.Typer(
    no_args_is_help=True, help="Staffeer — ranked, explainable consultant shortlists."
)

_DATA_OPTION = typer.Option(
    None, "--data", help="Path to the demand-supply workbook (overrides $STAFFEER_DATA)."
)


def _build_matcher_config(data: str | None, semantic: bool = False) -> StaffeerConfig:
    """Build a StaffeerConfig with optional data-path override and semantic flag."""
    config = StaffeerConfig.from_env()
    if data:
        config = config.model_copy(update={"data_path": data})
    if semantic:
        config = _semantic_config(config)
    return config


def _semantic_config(config: StaffeerConfig) -> StaffeerConfig:
    """Enable semantic search and validate milvus_path; exit 1 if unset."""
    if not config.milvus_path:
        typer.echo("error: STAFFEER_MILVUS_PATH is required to use --semantic.", err=True)
        raise typer.Exit(code=1)
    return config.model_copy(update={"semantic_enabled": True})


def _upsert_consultant(matcher: Matcher, consultant: Consultant) -> None:
    """Scrub, build an IndexItem, and upsert one consultant into the semantic index."""
    scrubbed = matcher.pii.scrub(_build_consultant_summary(consultant)).text
    item = IndexItem(
        id=consultant.id,
        text=scrubbed,
        namespace="skills",
        metadata={"location": consultant.location, "state": str(consultant.state)},
    )
    matcher.semantic_index.upsert(item)
    typer.echo(f"indexed: {consultant.id}")


def _index_all(matcher: Matcher) -> None:
    """Upsert every beach consultant into the semantic index; warn when supply is empty."""
    consultants = list(matcher.supply.consultants(*matcher.include_states))
    if not consultants:
        typer.echo("warning: no beach consultants found; index is empty.", err=True)
    for consultant in consultants:
        _upsert_consultant(matcher, consultant)


@app.command()
def index(data: str | None = _DATA_OPTION) -> None:
    """(Re)build the semantic index from supply data; idempotent."""
    config = _semantic_config(_build_matcher_config(data))
    try:
        _index_all(build_matcher(config))
    except StaffeerError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Index built.")


@app.command()
def roles(data: str | None = _DATA_OPTION) -> None:
    """List the open roles available to match against."""
    matcher = build_matcher(_build_matcher_config(data))
    for role in matcher.supply.open_roles():
        typer.echo(f"{role.id}: {role.title} — {role.location} [{role.priority.value}]")


def _match_role(matcher: Matcher, role_id: str, show_excluded: bool) -> None:
    """Look up role_id, run matching, and print shortlist; exits 1 when role not found."""
    try:
        role = matcher.supply.role(role_id)
    except SupplyDemandError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    shortlist = matcher.match(role)
    typer.echo(f"Role {role.id}: {role.title} — {role.location}")
    _print_shortlist(shortlist, show_excluded)


@app.command()
def match(
    role_id: str,
    data: str | None = _DATA_OPTION,
    show_excluded: bool = typer.Option(
        False, "--show-excluded", help="Also list excluded consultants and why."
    ),
    semantic: bool = typer.Option(
        False, "--semantic", help="Enable semantic matching via vector search."
    ),
) -> None:
    """Print the ranked beach shortlist for the role with id ROLE_ID."""
    _match_role(build_matcher(_build_matcher_config(data, semantic)), role_id, show_excluded)


def _build_llm_config(data: str | None, semantic: bool) -> StaffeerConfig:
    """Build an LLM-enabled config; exits 1 when OPENROUTER_API_KEY is absent."""
    config = _build_matcher_config(data)
    if not config.openrouter_api_key:
        typer.echo("error: OPENROUTER_API_KEY is required for free-text matching.", err=True)
        raise typer.Exit(code=1)
    llm_config = config.model_copy(update={"llm_enabled": True})
    return _semantic_config(llm_config) if semantic else llm_config


def _parse_and_match(query: str, llm_config: StaffeerConfig, show_excluded: bool) -> None:
    """Parse free-text query into a role and print shortlist; exits 1 on wiring or parse error."""
    try:
        role_parser = build_role_parser(llm_config)
        matcher = build_matcher(llm_config)
    except StaffeerError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    try:
        role = role_parser.parse(query)
    except (ValueError, LLMReasonerError) as exc:
        typer.echo(f"error: could not parse role description — {exc}", err=True)
        raise typer.Exit(code=1) from exc
    shortlist = matcher.match(role)
    typer.echo(f"Role (free-text): {role.title} — {role.location}")
    _print_shortlist(shortlist, show_excluded)


@app.command()
def match_text(
    query: str,
    data: str | None = _DATA_OPTION,
    show_excluded: bool = typer.Option(
        False, "--show-excluded", help="Also list excluded consultants and why."
    ),
    semantic: bool = typer.Option(
        False, "--semantic", help="Query the semantic index (requires STAFFEER_MILVUS_PATH)."
    ),
) -> None:
    """Match a free-text role description against the beach."""
    _parse_and_match(query, _build_llm_config(data, semantic), show_excluded)


def _print_shortlist(shortlist: Shortlist, show_excluded: bool) -> None:
    """Print the ranked shortlist and, when requested, the excluded consultants."""
    if not shortlist.matches:
        typer.echo("No eligible consultants on the beach.")
    for position, candidate in enumerate(shortlist.matches, start=1):
        typer.echo(_format_match(position, candidate))
    if show_excluded and shortlist.excluded:
        typer.echo("\nExcluded:")
        for result in shortlist.excluded:
            typer.echo(_format_excluded(result))


def _skill_detail(match: Match) -> str:
    """Return the detail string from the skills factor, or empty string when absent or blank.

    Returns empty string in two distinct cases:
    - No skills ExplanationFactor exists (role had no required skills or domain omitted it).
    - A skills factor exists but its ``detail`` field is the empty string (e.g. default
      ``SkillScore()``). Both cases suppress the ``skills:`` line in the output, which is
      intentional: an empty detail string carries no information worth surfacing.
    """
    for factor in match.explanation.factors:
        if factor.source == SKILLS_SOURCE and factor.detail:
            return factor.detail
    return ""


def _format_match(position: int, match: Match) -> str:
    """A consultant's rank, identity, score, and the factors behind it."""
    consultant = match.consultant
    grade = consultant.grade or "n/a"
    head = (
        f"{position}. {consultant.name} ({grade}, {consultant.location}) — score {match.score:.2f}"
    )
    factors = "\n".join(
        f"     - {factor.source}: {factor.summary}" for factor in match.explanation.factors
    )
    skill_detail = _skill_detail(match)
    skill_block = f"\n     skills: {skill_detail}" if skill_detail else ""
    return f"{head}\n{factors}{skill_block}"


def _format_excluded(result: EligibilityResult) -> str:
    """An excluded consultant and the hard constraints they failed."""
    reasons = "; ".join(failure.reason for failure in result.failures)
    return f"  - {result.consultant.name} ({result.consultant.location}): {reasons}"


def main() -> None:
    """Console-script entry point (`staffeer`): load `.env`, then dispatch commands."""
    load_env_file()
    app()

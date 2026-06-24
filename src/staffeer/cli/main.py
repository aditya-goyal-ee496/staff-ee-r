"""Typer CLI — the driving adapter for the matcher (I1, `docs/tasks/02-beach-matching.md`).

Two commands: `roles` lists the open roles in the workbook, and `match ROLE_ID` prints the
ranked, explained beach shortlist for one role (with `--show-excluded` to see why others were
dropped). The CLI only presents; all wiring goes through `build_matcher` and `build_role_parser`,
never adapters directly (`docs/tasks/parallelization-guide.md`).
"""

from __future__ import annotations

import typer

from staffeer.composition import build_matcher, build_role_parser
from staffeer.config import StaffeerConfig
from staffeer.domain.errors import SupplyDemandError
from staffeer.domain.explain import SKILLS_SOURCE
from staffeer.domain.matcher import Matcher
from staffeer.domain.models import EligibilityResult, Match, Shortlist
from staffeer.ports.reasoner import LLMReasonerError

app = typer.Typer(
    no_args_is_help=True, help="Staffeer — ranked, explainable consultant shortlists."
)

_DATA_OPTION = typer.Option(
    None, "--data", help="Path to the demand-supply workbook (overrides $STAFFEER_DATA)."
)


def _matcher(data: str | None) -> Matcher:
    """Build the matcher from env config, with an optional workbook-path override."""
    config = StaffeerConfig.from_env()
    if data:
        config = config.model_copy(update={"data_path": data})
    return build_matcher(config)


@app.command()
def roles(data: str | None = _DATA_OPTION) -> None:
    """List the open roles available to match against."""
    for role in _matcher(data).supply.open_roles():
        typer.echo(f"{role.id}: {role.title} — {role.location} [{role.priority.value}]")


@app.command()
def match(
    role_id: str,
    data: str | None = _DATA_OPTION,
    show_excluded: bool = typer.Option(
        False, "--show-excluded", help="Also list excluded consultants and why."
    ),
) -> None:
    """Print the ranked beach shortlist for the role with id ROLE_ID."""
    matcher = _matcher(data)
    try:
        role = matcher.supply.role(role_id)
    except SupplyDemandError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    shortlist = matcher.match(role)
    typer.echo(f"Role {role.id}: {role.title} — {role.location}")
    _print_shortlist(shortlist, show_excluded)


@app.command()
def match_text(
    query: str,
    data: str | None = _DATA_OPTION,
    show_excluded: bool = typer.Option(
        False, "--show-excluded", help="Also list excluded consultants and why."
    ),
) -> None:
    """Match a free-text role description against the beach."""
    config = StaffeerConfig.from_env()
    if data:
        config = config.model_copy(update={"data_path": data})
    if not config.openrouter_api_key:
        typer.echo("error: OPENROUTER_API_KEY is required for free-text matching.", err=True)
        raise typer.Exit(code=1)
    llm_config = config.model_copy(update={"llm_enabled": True})
    role_parser = build_role_parser(llm_config)
    matcher = build_matcher(llm_config)
    try:
        role = role_parser.parse(query)
    except (ValueError, LLMReasonerError) as exc:
        typer.echo(f"error: could not parse role description — {exc}", err=True)
        raise typer.Exit(code=1) from exc
    shortlist = matcher.match(role)
    typer.echo(f"Role (free-text): {role.title} — {role.location}")
    _print_shortlist(shortlist, show_excluded)


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
    """Console-script entry point (`staffeer`)."""
    app()

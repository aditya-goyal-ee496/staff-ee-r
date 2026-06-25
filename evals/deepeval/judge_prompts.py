"""Versioned LLM-judge prompts for relevance and faithfulness metrics.

Prompts are versioned here and NOT inlined elsewhere.  When a prompt changes,
bump the version comment and record the rationale in a commit message so the
history is auditable alongside the eval suites that use them.
"""

RELEVANCE_JUDGE_PROMPT = """\
# v1 2026-06-25
You are a staffing quality judge.  Given a role description and a ranked shortlist of
consultant names, score how relevant the shortlist is to the role on a scale of 0.0 to 1.0.

1.0 = every consultant on the shortlist directly matches the role's required skills and location.
0.0 = no consultant is relevant to the role at all.

A score of exactly 1.0 for a non-trivial role is suspicious — it may indicate the
scenarios are too easy (coverage warning).

Role description: {role_description}
Shortlist: {shortlist}

Respond with a single float between 0.0 and 1.0, and nothing else.
"""

FAITHFULNESS_JUDGE_PROMPT = """\
# v1 2026-06-25
You are a staffing rationale auditor.  Given a consultant's skill profile and a rationale
dict (name → list of explanation factor summaries), score whether each rationale claim is
grounded in the consultant's actual skills on a scale of 0.0 to 1.0.

1.0 = every claim in the rationale can be traced directly to a skill in the profile.
0.0 = the rationale fabricates claims not supported by any skill in the profile.

A score of exactly 1.0 for a non-trivial rationale is suspicious — coverage warning.

Consultant profile: {consultant_profile}
Rationale: {rationale}

Respond with a single float between 0.0 and 1.0, and nothing else.
"""

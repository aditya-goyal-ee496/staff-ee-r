# System Non-Functional Requirements (Quality Attributes)

The guiding principles the Staffeer matcher is held to. These are **quality attributes** — the
*how well* the system must behave — distinct from the engineering principles in this directory
(which govern *how the code is written*). They are mirrored in the human-facing brief
(`README.md` → "Guiding principles for the system"); keep the two in sync.

When a design or scoring decision trades one of these against another, make the trade-off
explicit (an ADR in `docs/adr/`), never silently.

## The attributes

- **Accurate & Relevant** — is it correct, and did it answer what was actually asked?
  Track-based systems (e.g. policy bots) have ground truth, so accuracy is measurable;
  open-ended systems lean on relevancy, scored by an LLM-as-judge and backed by user behaviour.
  Deterministic hard-constraint checks (location, dates) must be *accurate* and repeatable; soft
  fit is judged on *relevance*.

- **Repeatable & Predictable** — variance isn't always bad. In regulated/high-stakes contexts
  inconsistency is a trust failure; in creative/open-ended ones it's desirable. The job is to
  decide, deliberately, *where* variance is allowed — hard constraints are deterministic; soft
  judgment (fit, adjacency, feedback weighting) may use the LLM, with its reasoning surfaced.

- **Explainable & Referenceable** — the system can show its reasoning (explainability) and trace
  each output back to a specific, verifiable source (referenceability). Every recommendation
  states *why* it ranked where it did, *which source* backs each claim, and *what gaps* remain.
  An unexplained match is a bug, not a feature.

- **Secure & Governed** — access, data exposure, and the decisions the system may make stay
  inside set limits; plan for the breach and for bowing out cleanly. PII is scrubbed before it
  reaches an LLM; the system explains gaps rather than fabricating a match. See `security.md`.

- **Effective & Efficient** — fast and cheap means nothing if the user's problem isn't solved;
  watch hidden costs (work that looks efficient but needs heavy manual rework). Log LLM cost
  signals (model, tokens, latency) for auditability.

- **Reputation & Ethics** — a single AI mistake can do lasting brand damage; the system must
  respect brand values, regulatory obligations, and ethical lines (e.g. removing human bias while
  forming high-performing teams), and hold itself to them — never removing the human from the
  final decision.

## Why these matter for evals

These attributes drive the eval strategy (`evals/`): negative scenarios are mandatory, a
relevance suite that scores 100% is treated as under-covered (insufficient exploration), and
deterministic hard-constraint evals are the exception that must be perfect. See `testing-principles.md`.

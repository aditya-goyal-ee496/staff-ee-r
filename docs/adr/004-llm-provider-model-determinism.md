# ADR-004: LLM provider, model selection, and determinism controls for the soft-scoring reasoner

## Status: Accepted

## Context

Slice 06 activates the `LLMReasoner` port and wires in a concrete DSPy+OpenRouter adapter
(`adapters/dspy_openrouter.py`) to perform soft assessment of consultant fit. The slice also
defines how the reasoner behaves in low-confidence scenarios: it must abstain rather than
fabricate evidence when confidence is insufficient.

The LLM provider and model choice has implications for:

1. **Determinism & repeatability** — hard constraints (location, start date) must be
   deterministic and predictable; soft judgment (fit, willingness) may use an LLM but its
   variance is bounded and intentional.
2. **Cost & latency** — the dev team will iterate heavily; production inference must be
   affordable and latency-acceptable.
3. **Abstention semantics** — when the LLM is uncertain, the system must refuse to score
   rather than fabricate evidence; this is expressed as confidence < 0.3 → `abstained=True`.
4. **Versioning & eval reproducibility** — DSPy signatures and prompts are versioned;
   changes require eval results in the PR to verify no regression.

Two provider options were considered: OpenAI (GPT-4o-mini) and OpenRouter (vendor-agnostic,
lower cost for dev/testing, same API for future provider swaps). OpenRouter was chosen for
its flexibility and cost profile during development.

## Decision

Adopt **OpenRouter with `openai/gpt-4o-mini` as the default model**, with **temperature=0.0 for
all LLM tasks** (both hard-reasoning and soft-scoring), **and a low-confidence abstention
threshold of 0.3**.

### Provider & Model

- **LLM provider:** OpenRouter (`https://openrouter.ai/`)
- **Default model:** `openai/gpt-4o-mini`
- **Model selection:** Configured via environment variable `OPENROUTER_MODEL` (defaults to
  `openai/gpt-4o-mini`, the vendor-prefixed form required by OpenRouter); local model execution
  also supported for development via `OPENROUTER_BASE_URL`.
- **API key:** `OPENROUTER_API_KEY` from environment (required for integration tests and live
  inference).

### Determinism & Temperature Controls

- **Hard-reasoning tasks (temperature=0.0):** Role parsing from free text, constraint
  extraction (location, start date, seniority). These are deterministic by domain rule and
  must not vary across runs; `temperature=0.0` pins the LLM output.
- **Soft-scoring tasks (temperature=0.0):** Consultant fit assessment, feedback sentiment,
  adjacency willingness. Temperature is fixed at 0.0 to ensure reproducible evals and a
  consistent audit trail. Any change to this policy requires a follow-up ADR with supporting
  eval results demonstrating the benefit outweighs the loss of reproducibility.
- **Provider-side temperature compliance:** Some models routed via OpenRouter may silently
  ignore the `temperature` parameter. The pinned default model (`openai/gpt-4o-mini`) is
  verified to honour `temperature=0.0`. If the model is changed via `OPENROUTER_MODEL`, the
  integration-test suite must pass consistency checks before the change is accepted into `main`.
  Any model that does not reliably honour `temperature=0.0` must not be used as the default.
- **DSPy signatures:** All LLM calls use versioned DSPy signatures (`SoftAssessment_v1`,
  `RoleParser_v1`, etc.). A signature change is a contract change and requires:
  1. Updated `docs/tasks/06-llm-reasoning-ranking.md` notes section.
  2. Eval results in the PR showing no regression.
  3. New ADR if the change is material (e.g., new output field, drastically different prompt).

### Abstention & Low-Confidence Handling

- **Confidence threshold:** When the LLM returns `confidence < 0.3`, the reasoner treats it as
  abstention (`SoftAssessment.abstained=True`).
- **Validation:** `SoftAssessment` model validator enforces:
  - If `confidence < 0.3`, then `abstained=True` (automatic).
  - If `abstained=True`, then `score=0.0`, `evidence=()`, `cited_sources=()`, and
    `summary=""` (these are forced to their null values).
- **Rationale:** Low confidence signals insufficient evidence to score. Rather than presenting
  a fabricated score and evidence trail, the system explicitly signals "I cannot decide here;
  a human must review." This keeps the matcher accountable to the core principle:
  "Explainable over clever."

### Logging & Observability

- **LLM calls are logged** with model name, token counts (prompt + completion), latency,
  and output confidence. Logging is structured and never includes raw PII (all text is
  scrubbed before the LLM call, per slice 04).
- **Signature versions are logged** so audit trails can trace which version of a signature
  produced a given result.

## Consequences

**Good**

- **Cost and iteration speed:** OpenRouter with GPT-4o-mini is significantly cheaper than
  GPT-4 for development iteration, enabling fast eval feedback loops.
- **Flexibility:** OpenRouter's API is vendor-agnostic; swapping to Anthropic, local models,
  or future providers is a configuration change, not a code rewrite.
- **Explainability & governance:** Low-confidence abstention is a structural commitment:
  the system never presents an unjustified score. This aligns with the core principle and
  makes the system auditable — every shortlist entry is defensible.
- **Reproducibility:** Temperature=0.0 for hard reasoning ensures contract-test reproducibility;
  versioned signatures ensure eval results are traceable to code.
- **Testability:** Stubbed reasoners (NullLLMReasoner, StubLLMReasoner) and test fixtures mean
  the entire soft-scoring pipeline runs with no network I/O, keeping tests fast and
  deterministic.

**Costs / trade-offs**

- **Dev dependency on OpenRouter:** Development iteration requires an OpenRouter API key and
  internet connectivity for integration tests. Mitigated by making all tests pass with
  NullLLMReasoner (no network required) and gating integration tests on key presence.
- **Low-confidence abstention may feel "incomplete."** A shortlist that abstains on some
  candidates might appear shorter or less decisive than one that always scores. This is
  intentional — it reflects epistemic honesty and is preferable to fabricated confidence.
  Any change to the 0.3 threshold must be recorded in a follow-up ADR accompanied by eval
  results from real or representative data showing the new threshold is better calibrated.
- **Signature versioning overhead:** Every prompt change requires a version bump and eval
  validation. This is intentional — it prevents silent regression and keeps the audit trail
  clear.

## Follow-ups (future ADRs or slices)

- **Model selection policy** — if production scale demands a shift to a cheaper or faster model,
  the decision and eval results should be recorded in a follow-up ADR.
- **Temperature tuning for production** — if soft-scoring results benefit from non-zero
  temperature, a follow-up ADR is required; it must include eval results demonstrating the
  benefit and confirming that the chosen model honours the parameter.
- **Confidence calibration** — after observing real-world runs, the 0.3 threshold may be
  adjusted if domain experience suggests a different bound is more appropriate.

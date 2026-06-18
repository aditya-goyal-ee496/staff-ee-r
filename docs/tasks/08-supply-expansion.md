# Slice 08 — Supply expansion (roll-offs & new joiners)

**Goal:** extend matching beyond the beach to people rolling off (free on a future date) and new
joiners (joining on a future date), honouring date buffers, confidence, and unverified skills.

**Type:** Feature · **Priority:** P1 · **Depends on:** I1 + (I2 or I4 weighting seam)

> **Parallelization.** Mostly **Track A + B** work, and largely parallel because the model fields
> it needs (`confidence`, `skills_verified`, provenance, `available_from`) were **pre-baked into
> the frozen `Consultant` in C1** — so no breaking model change is required here. Lands as
> integration slice **I5**: a `--include rolling_off,new_joiner` flag + a provenance-weighting
> `ScoreContribution`. See [`parallelization-guide.md`](parallelization-guide.md).

## Acceptance criteria

- [ ] `match` can include `rolling_off` and `new_joiner` supply states (flag-controlled).
- [ ] Start-date constraint uses each person's true availability (roll-off / join date) + buffer.
- [ ] Roll-off **confidence** (low/high) is surfaced and can downweight or flag a candidate.
- [ ] New joiners' **unverified** skills are flagged in the explanation and weighted accordingly.

## Tasks

- [ ] **Availability** — confirm adapter maps roll-off/join dates to `available_from`; add
      `confidence` and `skills_verified` provenance to `Consultant`.
- [ ] **Constraint** — start-date logic already general; add tests for roll-off-after-start+buffer
      (excluded) and confirmed-roll-off-before-start (included).
- [ ] **Scoring** — apply provenance weighting (unverified skills, low confidence) via the config;
      keep it explainable.
- [ ] **CLI** — `--include rolling_off,new_joiner` (default beach); show availability + confidence.
- [ ] **Tests** — buffer boundaries, low-confidence flagging, unverified-skill weighting; a
      **late-roll-off no-match** negative scenario.
- [ ] **Evals** — add mixed-supply scenarios to the golden set.

## Notes

- Roll-off dates in the sheet are final (30-day notice incorporated) — do not re-estimate them.

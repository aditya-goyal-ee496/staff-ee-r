# TODO Execution Rules

## Workflow for Executing TODO Items

When working with TODO lists (TODO.md files), always follow this execution workflow:

1. **Pick the task** and mark it in progress (`[~]`).
2. **Spec first (SDD).** If the task introduces or changes a contract (a port, a domain value
   object, or a pure-function group), author/confirm its **spec** and **request approval of the
   spec before writing implementation code** (`docs/rules/spec-driven-development.md` RULE-001;
   use `/specify`). Skip only when the task is purely additive against an already-approved,
   frozen contract.
3. **Write the contract/unit test from the spec** — the executable form of the spec
   (`tests/contract/` for ports). It should fail before implementation exists.
4. **Implement this task in THE SIMPLEST WAY POSSIBLE** that makes the test pass.
5. **Run the quality checks**:
    -   format
    -   test
    -   lint
6. **Ask for review and WAIT FOR APPROVAL**
7. **Mark the TODO item as complete with [X]**
8. **Commit the change to Git** (observing rules/git-rules.md) when approved

## Key Principles

-   **Spec is the source of truth**: the spec/contract is authored and approved *before*
    implementation (`docs/rules/spec-driven-development.md`); code is derived from it.
-   Always implement the simplest solution that meets requirements
-   Never proceed to the next task without explicit approval
-   All quality checks must pass before requesting review
-   Wait for user review before marking items complete
-   Follow git commit rules when making changes
-   A frozen, approved contract is what lets independent workstreams run **in parallel** — do
    not change one silently; amend the spec and re-approve (`spec-driven-development.md` RULE-004).

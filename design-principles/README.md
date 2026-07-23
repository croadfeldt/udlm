# UDLM Design Principles

This directory holds UDLM's normative principles. They are split into five files by **kind of statement**, not by topic — each file answers a different question and owns a distinct ID namespace, so a rule lives in exactly one place. Read this index first to know which file a given principle or policy ID belongs to.

| File | Answers | ID namespace | Read it when you need… |
|------|---------|--------------|------------------------|
| [`core-tenets.md`](core-tenets.md) | *What is UDLM forbidden from doing?* — the hard boundaries that separate the data model from Policy and from realization | `T1`–`T6` | to know whether a behavior belongs in UDLM at all (custodian-not-mutator, transformation-is-Policy, adopt-by-reference) |
| [`design-priorities.md`](design-priorities.md) | *When principles conflict, how do we choose?* — the four ranked priorities and the decision framework, plus the profile and authority-tier vocabularies | `Priority 1`–`4` | to resolve a trade-off (security vs ease-of-use), or to look up the profile / authority-tier vocabulary |
| [`cross-cutting-requirements.md`](cross-cutting-requirements.md) | *What must hold everywhere, on every entity?* — the cross-cutting non-functional obligations | `P0`–`P4` | to check an always-on obligation (auditability, observability, typed dependency graph, structural sovereignty) |
| [`adopted-standards.md`](adopted-standards.md) | *How does an external standard enter UDLM?* — the absorb / embed / adopt disposition and the net-negative test | — (procedure + constructs) | to bring in an industry standard (FOCUS, OIDC, TOSCA) by reference rather than absorption |
| [`data-contracts.md`](data-contracts.md) | *What does the substrate require of persistence?* — the data-contract principle and the four persistent domains | `DSC-001`–`DSC-007` | to check a persistence/storage obligation (append-only, versioning, tamper-evidence, tenant isolation) |
| [`naming-charter.md`](naming-charter.md) | *What is each thing called, and how do the axes relate?* — the canonical vocabulary + the `family`/`nature`/`archetype` collapse; settled once pre-0.1, then frozen (**Proposed**) | — | to look up the canonical term for a concept, or before proposing any rename |

## How the five relate

- **Tenets are boundaries; priorities are trade-offs; cross-cutting requirements are always-on obligations.** A tenet says *never*; a priority says *prefer, in this order*; a cross-cutting requirement says *on everything, without exception*. If a statement fits more than one, it lives with the strongest: a hard boundary is a tenet, not a priority.
- **`adopted-standards.md` and `data-contracts.md` are subject-specific** — one governs how external standards come in, the other governs persistence. Neither restates the tenets or priorities; they apply them.
- **Each rule has one home and one ID.** Prose in these files explains; the ID (a `T*`, `P*`, `INF-*`, or a `Priority`) is what conformance and reviews cite. Where a downstream document needs a rule, it **references the ID** — it does not restate the rule, so the two cannot drift.

## What is defined elsewhere (referenced, not redefined here)

- **The four lifecycle states** (Intent / Requested / Realized / Discovered) are defined in [`foundations/four-states.md`](../foundations/four-states.md); `data-contracts.md` states only the *persistence invariants* over them.
- **Versioning** is single-sourced in [`registry/VERSIONING.md`](../registry/VERSIONING.md).
- **Conformance levels and the wire-compatibility checklist** live in [`CONFORMANCE.md`](../CONFORMANCE.md); the principle files supply the required contracts, not the checklist.

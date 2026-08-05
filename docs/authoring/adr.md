# Authoring an ADR

An ADR is a **decision record** — a short, immutable justification of one UDLM data-model decision.
UDLM adopts the ADR/MADR format by reference; it does not coin its own (see
[`../adr/README.md`](../adr/README.md) — the index, where every ADR earns a one-line row carrying its
gist). This HOWTO is the procedure; follow it and the terminology, single-source, and link gates
accept it.

> **Read once, first:** [`README.md`](README.md) (the universal contract), the ADR index above (how
> ADRs are written — the "Background — read first" discipline), and the exemplar below.

## 1. When to use it — and when not

Author an ADR when you make a **decision about the model** that a third party must be able to
reconstruct: a new mechanism, a boundary ruling, a reference-shape choice, a term retirement. An ADR
records the **why**; it points to the schema and the model, never reproduces them.

Do **not** reach here for:

- proving a capability *behaves* — that is a Use Case ([`use-case.md`](use-case.md));
- narrating a lifecycle across types — that is a flow ([`flow.md`](flow.md));
- a decision recorded as **machine-validated data** rather than prose — that is a `DecisionRecord`
  instance under `registry/instances/` (the `ADR-<FAMILY>-NNN` namespace, e.g. `ADR-PROV-004`),
  validated against [`../../registry/decision-record.schema.json`](../../registry/decision-record.schema.json).
  A file-based ADR and an instance record are the same entity in two homes; the schema's own
  description says an ADR *is* a `DecisionRecord` whose anchor is architecture. Use the instance form
  when the decision needs to be queryable/attested; use the file form (this HOWTO) for the narrative
  record.

**Reduce before you coin** (README's universal rule T7): show no existing mechanism composes to cover
the decision before you record a new one.

## 2. The steps, in order

1. **Claim the next number.** ADRs are locally sequenced `ADR-0NN`; create
   `docs/adr/ADR-0NN-<kebab-title>.md`. A control-plane decision is cited as `DCM ADR-0NN` and lives
   in the DCM repo — never renumber into the local space.
2. **Write the header** — `**Status:**` (Proposed until engineering accepts), `**Date:**`, `**Type:**`
   (Architecture Decision Record — a `DecisionRecord`, architecture scope).
3. **Write the on-ramp: `**Background — read first**`** (DOC-001). Cite each dependency **once, with
   what it settles** — never a bare number ("ADR-051 — identity = a spec's normative bytes, the digest
   and publish law", not "see ADR-051"). Label it as the on-ramp a reader with the context skips.
   Foundational material is a *denoted reading path*, not re-taught inline.
4. **Write the body** — `## Context` (the specific forces; assume domain literacy), `## Decision`
   (active, one decision-area, numbered clauses), `## Consequences` (only the non-obvious
   easier/harder). Cut anything that doesn't move the decision.
5. **Add `## The standards, and what each settles here`** — a table: each adopted standard → the rule
   it contributes → how it is realized here. (ADR-055's table adopts JSON Schema / OpenAPI / Spectral
   this way.)
6. **Add the `## Data · Policy · Provider` lens** — the three foundational abstractions, required on
   every ADR: *Data* = what UDLM models/holds, *Policy* = what DCM decides/computes, *Provider* = what
   is declared possible and executes. A decision that cannot name all three (or say "n/a, because…")
   is not fully scoped.
7. **State the scope edge** — a "what this does not decide" boundary (the UDLM/DCM split, ADR-008)
   where it applies.
8. **Add the index row** — one line in [`../adr/README.md`](../adr/README.md)'s table carrying the
   ADR's gist.

**Immutability (ADR-051).** Once Accepted, an ADR is **not edited in place** — a new ADR *supersedes*
it, and the superseded one is marked, not rewritten. Amendments are new records. This is the same
record discipline the whole registry uses for immutable artifacts.

## 3. The completeness checklist — and the gate for each

| Ships with the ADR | Enforced by |
|---|---|
| No retired terminology in the prose (e.g. no `provider_extensions`, no merged-away policy names) | `tests/check_terminology.py` — TERM-001 |
| Any rule-ID you *define* lives only in its registered home file; elsewhere you *cite* it | `tests/check_single_source.py` — one prefix = one home (ADR-028); an out-of-home definition fails |
| Every relative Markdown link resolves (Background refs, the index row, the DCM/spec pointers) | `tests/check_links.py` |
| The Data · Policy · Provider lens is present | convention (the required lens; the instance schema makes it a required field) |
| The Background on-ramp cites each dependency once, with its gist | DOC-001 (author's job — no gate writes the clear sentence) |

**On rule-IDs (the single-source trap).** An ID-first Markdown table row (`` | `PFX-NNN` | … | ``) is
read by the gate as *defining* that rule. An ADR usually **cites** rules, so keep rule-IDs in prose or
in a non-leading table cell; only the prefix's registered home file may define them. Coin a new prefix
in `registry/rule-id-registry.yaml` **before** you use it.

## 4. A worked pointer

Copy [`../adr/ADR-055-in-spec-examples.md`](../adr/ADR-055-in-spec-examples.md) — it is the exemplar
for every section: a `Background — read first` on-ramp (rule-36, ADR-051, the coverage gate, each cited
once with what it settles), a one-decision-area body with numbered clauses, the
"standards, and what each settles here" table, the Data · Policy · Provider lens, and a scope edge. Its
one-line index row in `../adr/README.md` shows the gist a new ADR must supply.

## 5. Run the gates

```console
$ python3 tests/check_terminology.py && python3 tests/check_single_source.py && python3 tests/check_links.py
550 files scanned, 0 terminology violation(s)
rule-id single-source: 46 registered prefix(es); 400 rule IDs across the normative surface; 0 collide (0 baselined); 2 sanctioned co-home(s), 0 spread-debt entr(y/ies).
OK — every rule-ID prefix is registered; every ID has a single definition.
232 files scanned, 0 broken link(s)
```

The pass signals are `0 terminology violation(s)`, the single-source `OK — …` line, and `0 broken
link(s)`. All three run in `./scripts/signoff.sh` with the full set.

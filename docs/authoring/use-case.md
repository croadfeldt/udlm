# Authoring a Use Case

A Use Case is a **corpus scenario** — one YAML file that asserts the model can express, check, and
gap-detect a capability. It is the model-side twin of a DAV analysis set: the same schema, valid in
both corpora unchanged (see [`../../use-cases/README.md`](../../use-cases/README.md) — the corpus is
what proves a type's capability axes, not the spec alone). This HOWTO is the procedure; follow it and
the two UC gates accept your files.

> **Read once, first:** [`README.md`](README.md) (the universal contract — a resource type ships a
> Use Case + example + flow in a `coverage:` block) and the corpus README above.

## 1. When to use it — and when not

Author a Use Case when you add or change a capability and need to prove it *behaves*: a new resource
type, a new edge nature, a refusal path, a composite. A UC is a **behavioral assertion**, not an
example instance.

Do **not** reach here for:

- a **worked instance** of a type — that is `spec.examples`, in the spec itself ([`adr.md`](adr.md)
  neighbor: ADR-055 — the example lives in the spec, validated against its own schema, not as a side
  file);
- a **lifecycle narrative** across several types — that is a flow ([`flow.md`](flow.md));
- a **decision** about the model — that is an ADR ([`adr.md`](adr.md)).

A UC references a decision; it never argues one.

## 2. The steps, in order

1. **Pick the family directory** under `use-cases/` (e.g. `use-cases/storage/`,
   `use-cases/must-reject/`). One family per capability area.
2. **Author the file** `NNN-short-kebab-handle.yaml`. Copy the closest exemplar; the shape is:
   - `uuid: uc-<uuidv4>` — fresh per file (the identity contract; never reuse).
   - `handle: <family>/<kebab>` and `version: 1.0.0`.
   - `scenario.description` — a single dense paragraph: the intent, what realizes (or refuses), and
     the one thing it *stresses*.
   - `scenario.actor.persona` + `scenario.perspectives[]` — **canonical personas only** (step 3).
   - `scenario.intent`, `scenario.success_criteria[]` — the pass conditions, in the reader's terms.
   - `scenario.dimensions.*` — the six closed-vocabulary axes (step 3).
   - `scenario.expected_domain_interactions[]` — one line each for `data` / `policy` / `provider` /
     `audit`.
   - `generated_by` + `tags[]`.
3. **Resolve every closed vocabulary before you invent a value.**
   - Dimensions: pick each `scenario.dimensions.*` value from
     [`../../use-cases/DIMENSION-VOCABULARY.yaml`](../../use-cases/DIMENSION-VOCABULARY.yaml). It is the
     single source of truth for the six axes (`lifecycle_phase`, `resource_complexity`,
     `policy_complexity`, `provider_landscape`, `governance_context`, `failure_mode`). A genuinely new
     value is a deliberate edit **there first**, then the UC — never an off-list string in the UC.
   - Personas: `actor.persona` and every `perspectives[]` entry must be a canonical `id` (or a
     `folded_aliases` key) from [`../../use-cases/PERSONAS.yaml`](../../use-cases/PERSONAS.yaml). Each
     persona carries `objectives` — the demands your success_criteria should satisfy for that lens.
4. **Meet the per-type minimum: 2–3 UCs.** A type earns its corpus with a **positive** (happy path),
   a **negative / must-reject**, and — where it composes — a **composite**. The three storage
   exemplars are exactly this set (worked pointer below).
5. **For a must-reject UC, encode the refusal contract** (step 3 of the checklist).

## 3. The completeness checklist — and the gate for each

| Ships with the UC | Enforced by |
|---|---|
| Every `dimensions.*` value is in the dimension vocabulary | `tests/check_uc_dimensions.py` — **DIM-001**; an off-vocabulary value fails, naming the value, the axis, and any folded-alias fix |
| `actor.persona` resolves to a canonical persona | `tests/check_uc_personas.py` — **PER-001** |
| Every `perspectives[]` entry resolves to a canonical persona | `tests/check_uc_personas.py` — **PER-002** |
| A must-reject UC carries `must-reject` + `refusal-contract` tags | convention (the negative family, `use-cases/README.md`) |
| A must-reject UC's success = the refusal, honoring ADR-003's five elements | authored into `success_criteria` (no separate gate — this is the author's job) |
| No estate tokens (personal host/site names, estate IPs) | `tests/check_estate_tokens.py` |

**The refusal contract (must-reject UCs).** Success is the REFUSAL, and per
[ADR-003](../adr/ADR-003-data-mobility-and-process-validation.md) (data-mobility + process-validation
— the origin of the refusal-contract elements, as [`../../use-cases/PERSONAS.yaml`](../../use-cases/PERSONAS.yaml)
attributes them) the refusal must be **typed** (machine-matchable, distinct from not-found and
schema-invalid), **actionable** (surfaced, naming the constraint and its resolution), **whole** (no
silent partial or truncation), **non-leaking** (no reference escapes a boundary it was not released
for — ADR-041), and **auditable** (an immutable record of the decision). Write those five into
`success_criteria`, and tag the file `must-reject` + `refusal-contract`. The exemplar 002 does exactly
this: it refuses before realization, types the error as quota exhaustion, forbids silent truncation and
indefinite Pending, names requested-vs-available, and records the comparison.

**Estate-neutrality.** Keep every scenario estate-neutral: no personal host or site names, and use
RFC 5737 documentation ranges (`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`) rather than estate
private IPs (`10.0.x`). `tests/check_estate_tokens.py` scans for both and fails the build on a hit.

## 4. A worked pointer

Copy the storage triad — one complete per-type set:

- **Positive:** [`../../use-cases/storage/001-provision-volume-bound-to-pool.yaml`](../../use-cases/storage/001-provision-volume-bound-to-pool.yaml)
  — a Volume binds to a Pool's capacity and realizes with its declared properties.
- **Negative / must-reject:** [`../../use-cases/storage/002-volume-request-exceeds-quota-refused.yaml`](../../use-cases/storage/002-volume-request-exceeds-quota-refused.yaml)
  — the over-quota request is refused; carries the `must-reject` + `refusal-contract` tags and the
  five-element success criteria.
- **Composite:** [`../../use-cases/storage/006-composite-fileshare-backed-by-pool-dataset.yaml`](../../use-cases/storage/006-composite-fileshare-backed-by-pool-dataset.yaml)
  — a Pool → Dataset → FileShare chain realizes in dependency order (`resource_complexity:
  composite_service`).

## 5. Run the gates

```console
$ python3 tests/check_uc_dimensions.py && python3 tests/check_uc_personas.py
138 use case(s) checked, 0 off-vocabulary value(s)
138 use case(s) checked, 0 unresolved persona reference(s)
```

The pass signal is the trailing `0 off-vocabulary value(s)` and `0 unresolved persona reference(s)`
(the count rises as your files land). Both gates run in `./scripts/signoff.sh` with the full set.

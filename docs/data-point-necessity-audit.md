# Data-point necessity audit (review artifact, 2026-07-20)

> **Status: review artifact for engineering discussion, non-normative.** A pre-1.0 pass asking of each stored
> field: *does it earn its keep, or does it duplicate functionality?* Findings are proposals; each links where
> it is tracked. The goal is a lean data model where every stored point has real value.

## The discipline (the point behind the audit)

**A stored field must have a real consumer, or be a derived predicate — otherwise it is duplicated
functionality.** This is the data twin of T7 (*reduce to existing mechanisms*): T7 keeps the model from
coining redundant *primitives*; this keeps it from storing redundant *data points*. A classifier that (a)
nothing branches on and (b) is computable from data already present isn't a data point — it's a cached query,
and it should be *derived at query/policy time* (T2), not stored as source of truth.

**Method.** For each field: **distribution** (does it actually vary in the registry?), **consumers** (does any
policy / contract / validator / lifecycle rule branch on it?), and **derivability** (is it computable from
other present data?). A field that is invariant *or* has no consumer *and* is derivable is a candidate to drop
or derive.

## Findings

| Field | Disposition | Evidence | Tracked in |
|---|---|---|---|
| `entity_type` (Resource/Process shape) | **Derive** — drop stored value | 33 `Atomic` / 2 `Composite`; **0 consumers**; `multi ≡ has_constituents` | ADR-027 addendum (#172) |
| `lifecycle_archetype` | **Derive** — drop stored value | schema says *"inferred from `family`"*; 22 set, **0 consumers**; derivable | ADR-027 addendum (#172) |
| `family` | **Collapse into `nature`** (not delete) | *is* consumed (Process-block validation) — but only for the `nature` distinction | naming charter (#171) |
| `version` | **Decide: keep-for-convenience or derive** | duplicates the version segment in `$id`; validator-synced; derivable by parsing `$id` | this doc |
| `metering` / `priced_by` | **Watch** — don't entrench | both **PROPOSED** (ADR-COST-002); cost surface unvalidated | task #28 (Meteridian eval) |
| `portability` | **Keep** | varies (35 / 4 / 1); **consumed** (governance, provider-contract, validator); ADR-014 requires explicit declaration | — |
| `status` | **Keep** | genuine lifecycle state (active/deprecated/retired) | — |

## Detail on the non-obvious ones

- **`entity_type` shape / `lifecycle_archetype` — the two clean derivations.** Same pattern: a stored
  classifier with **zero behavioral consumers** that is computable from data already present (`entity_type`
  from the constituent list; `lifecycle_archetype` from `family`, per its own description). Derive both.
  *Dependencies (`depends_on`) are **not** the signal for the shape — that is "needs," not "owns"; an atomic
  resource has dependencies.* (ADR-027 addendum.)

- **`family` — a collapse, not a deletion.** It has real consumers (e.g. "a `Process` carries a `process`
  block"), but everything it is consumed *for* is the **`nature`** distinction. Retiring `family` means
  **repointing its consumers to `nature`**, which is why it belongs to the naming-charter collapse, not this
  audit's "drop" column.

- **`version` — controlled duplication.** The `version` field restates the version already embedded in `$id`
  (the two are kept in sync by a validator — the same sync that must be updated on every bump). It is
  *derivable* from `$id`. Kept today as a query convenience; the conscious call is keep-for-convenience or
  derive-from-`$id`.

- **`metering` / `priced_by` — proposed, so don't harden.** Two *sides* of the cost contract (measurable
  surface vs external cost-model reference), not duplicates of each other — but the whole cost surface is
  PROPOSED and unvalidated. Scrutinize when cost lands; don't entrench first.

## Recommendation — make the discipline standing

The redundancy clusters entirely in the **classifier axes** (shape / archetype / family) — the same place the
naming charter is already pointing — which is a good sign: the rest of the model earns its keep. To keep it
that way, add a standing review-sweep item:

> **Every new stored field must name a real consumer or be a derived predicate.** A classifier that nothing
> branches on, and that is computable from present data, is derived at query/policy time — not stored.

That turns this one-time pass into a ratchet, so redundant data points are caught at authoring time rather
than found in a later audit.

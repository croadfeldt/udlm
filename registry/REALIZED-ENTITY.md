# UDLM Realized Entity (instance) schema

`resource-type-spec.schema.json` defines a **type**; `realized-entity.schema.json` defines an
**instance** — the operational record of one entity (or Composite Entity) as it flows through the four
states. It is the data substrate **DCM reads and writes**; UDLM carries the records, DCM applies the
policy that produces them (`core-tenets.md` G3). Validate instances with `tools/validate.py`
(`registry/instances/*`); `instances/orders-db.json` is a worked example.

## What it carries — and the DCM capability it serves

| Field | Serves |
|---|---|
| `states.{intent,requested,realized,discovered}` | the **four-state lifecycle** — immutable snapshots; `realized` is the system of record |
| `generation` / `observed_generation` | realization-pending signal (observed < desired ⇒ in flight) |
| **`provenance`** (per dot-path history of layer/policy/actor/provider + timestamp + previous value) | **audit (#191 / E4)** — the record the Merkle chain consumes |
| **`ownership`** (per dot-path manager) | **field ownership / server-side apply (R4)** — offline conflict detection across providers |
| `dependencies` (resolved edges + bindings) / `constituents` | **dependency graph** + composite realization |
| `drift` (Discovered vs Requested) + `status.conditions` | **observability** + drift detection |
| `sovereignty` (zone/classification, realized from `immutable` type fields) | **sovereignty** — can't change without replace + Governance-Matrix re-eval |
| `audit` (Merkle `logHead` + `leafCount`) | **audit linkage** (`AUD-001/002`) |
| `type_version` / `type_ref` | **version pinning (E5)** — drift/validation measured against the exact contract realized |

That set is what the **v1.0 surface** must carry to be **complete for DCM capabilities**: lifecycle,
audit, observability, dependency graph, sovereignty, field ownership, drift, and version pinning all
have a home in the data. (UDLM v1.0 is still being defined — this realized-entity schema is part of
*expanding* that initial surface, not a post-1.0 refinement.)

## The boundary (where each piece is produced)
The instance record is **Data** — UDLM's. Everything that *populates* it is **Policy/DCM**: assembly
writes `provenance`/`ownership` and the `requested` snapshot; the Provider writes `realized` + `outputs`
+ `status`; discovery writes `discovered` + `drift`; DCM produces the `audit` Merkle chain. UDLM never
computes these — it holds them (T1/T2). Field values inside the snapshots are typed by the entity's
Resource Type Spec and are not re-validated here.

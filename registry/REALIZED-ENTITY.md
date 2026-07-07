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
| `audit` (Merkle `log_head` + `leaf_count`) | **audit linkage** (`AUD-001/002`) |
| `type_version` / `type_ref` | **version pinning (E5)** — drift/validation measured against the exact contract realized |
| `lifecycle_state` | the entity's current position in the four-state model (`Intent`/`Requested`/`Realized`/`Discovered` + terminal `Decommissioned`) — the ONE lifecycle enum (data-model-core §3) |
| `handle` | **advisory human identity** (identifier-scheme §3) — uuid is authoritative; handle disagreement at resolution is drift, not failure |
| `metadata` (display_name, description, attributed `notes[]`) | human-facing context; notes are auditable records, never anonymous mutable blobs (common-elements §8.2) |
| `adopted_standards` (per-standard negotiated binding) | **adopt-by-reference (T5)** — the realized record of DCM's version negotiation (requested/provider/effective version + translation) |
| `correlation_ids` (scheme + value natural keys) | **entity resolution across discovery sources** — one real resource, one uuid (dcm ADR-017 Decision C) |
| **`tenant_uuid`** (required) | **tenancy (TEN-001/003)** — the owning Tenant: the uuid of a `tenant_boundary` DCMGroup (`dcm-group.schema.json`); schema-required per data-model-core §5 [D3]. Brownfield stores migrate by minting their tenants and backfilling. `instances/example-tenant.yaml` is the worked example orders-db belongs to |

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

## State population paths (greenfield vs greening)

Two lifecycles populate the same record shape — what differs is *order* and *author*:

| State | Greenfield (forward, ADR-003) | Brownfield greening (reverse, dcm ADR-017) |
|---|---|---|
| `intent` | 1st — consumer declares | 4th — synthesized (`origin: discovered-derived`/`backfilled`), provider-agnostic, for DR/rehydration |
| `requested` | 2nd — DCM assembly (layers + policy) | 4th — backfilled with `origin: backfilled` |
| `realized` | 3rd — **the Provider's receipt** | 3rd — written at **claim/adoption** from the owning provider's discovered statement; never hand-authored |
| `discovered` | 4th — ongoing observation → drift | **1st** — attributed observation (`provider`, `at`, `time_source`); the record may live Discovered-only (unclaimed) until claimed |

`lifecycle_state` follows the same line: a brownfield record is `Discovered` until a provider
claims it — Realized is *earned*, not asserted. `correlation_ids` keep multi-source
observations resolved to one entity uuid on both paths.

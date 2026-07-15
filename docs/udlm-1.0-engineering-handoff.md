# UDLM 1.0 — Engineering Handoff

**Status:** Handoff (orientation, non-normative) — points at the normative surface, does not restate it.
**Audience:** the engineering team implementing UDLM 1.0 (the September release).
**What this settles:** where to start, the model you must hold in your head, where the authoritative truth lives, and how to check your work. Scope, use-case coverage, and exit criteria are settled separately in [`registry/UDLM-1.0-SCOPE.md`](../registry/UDLM-1.0-SCOPE.md) — read that for *what's in*; read this for *how to get oriented*.

---

## 1. What you're building

UDLM is the **data / contract / type** layer — the wire-compatible substrate. It is **not** the orchestrator; the runtime that consumes it is DCM. The boundary is one test (ADR-008): *"could a peer implement this differently and still be valid? Yes → it's DCM (runtime/policy); No → it's UDLM (data/contract)."* Every ambiguity resolves with that question. UDLM 1.0 is the substrate that **enables the 21 release use cases** (`UDLM-1.0-SCOPE.md` §3); DCM satisfies many success criteria at runtime over a UDLM shape — those are not 1.0 spec work.

**Implement against the `dev` profile.** The architecture and wire contracts are identical across the five profiles; only the required *floor* differs (`registry/instances/profile-*.yaml`). September builds and validates the 21 UCs against **dev**; the `sovereign`/`fsi` floors exist so the architecture is provably production-grade, not to be implemented first (`UDLM-1.0-SCOPE.md` §2).

**Valid-by-construction.** Everything is a typed record that validates against a JSON Schema. If it doesn't validate, it isn't UDLM. The validators are the definition of done (§5).

## 2. The model in one page

Hold these seven concepts and the rest follows:

1. **Four lifecycle states** — Intent → Requested → Realized → Discovered, immutable, linked by `entity_uuid` (`foundations/four-states.md`). The spine everything hangs on.
2. **Typed records + schemas** — each Resource Type is a spec validated by `resource-type-spec.schema.json`; each instance validates against its type. Identity is a UUID (RFC 9562 v4), advisory names are `handle`s (`contracts/identifier-scheme.md`).
3. **Data layering** — a request payload is assembled by merging ordered layers lowest-authority-first (base → core → intermediate → service → request; policy over the result), with **field-level provenance** — every field records the layer uuid that set it (`foundations/layering-and-versioning.md`; `registry/layer.schema.json`). This is how a standard base is reused and specialized per data center / rack / segment.
4. **Data references + immutable lineage** — a field points at shared governed data by object reference `{ref_uuid, ref_name, ref_version, reference_data_type}` (uuid authoritative, name/version advisory) instead of inlining. Referenced entities are **immutable** (a change mints a new uuid+version); lineage is a **single explicit `supersedes` DAG**; change-impact is derived from that DAG and cascades transitively up the reference graph (`registry/data-reference.schema.json`; `docs/adr/ADR-012-data-references.md`). Acting on impact is a DCM policy, never automatic.
5. **Provider capability declaration** — a provider declares, per capability, what it can fulfill: topology / mobility / operational primitives / sovereignty (`registry/provider-adopted-standards.schema.json`; `docs/adr/ADR-004-*`). Placement matches consumer requirements against this.
6. **Sovereignty & accreditation** — a declared sovereignty stance is a **claim**; trust requires a **1-1 match** with an **accreditation** (a verifiable credential: `proof` + `trust_anchor`) on provider × capability × jurisdiction × data-classification × plane, decided by a **two-gate** check (verify, then appraise). No match → `self_asserted` → not honored for sovereign placement (`governance/accreditation-and-authorization-matrix.md`; `registry/accreditation.schema.json`).
7. **Policy is separate from data** — layers and references carry *values*; policies *decide/transform* (`registry/policy.schema.json`; `contracts/policy-contract.md`). Keep them apart: a layer says "the zone is DMZ"; a policy says "DMZ workloads must use the DMZ egress."

## 3. The normative surface — where the truth lives

**Schemas (`registry/*.schema.json`) — the machine-checkable truth:**

| Schema | What it defines |
|---|---|
| `resource-type-spec.schema.json` | the meta-schema every Resource Type definition validates against |
| `realized-entity.schema.json` | a realized instance record (the `resource_type` discriminator) |
| `layer.schema.json` | a data layer — base/overlay/reference_data; `fields`, provenance, `supersedes` lineage |
| `data-reference.schema.json` | the object-reference shape `{ref_uuid, ref_name, ref_version, reference_data_type}` |
| `provider-adopted-standards.schema.json` | provider capability declaration (adopted standards + per-capability blocks) |
| `accreditation.schema.json` | a verifiable accreditation (`proof`, `trust_anchor`, scope) |
| `policy.schema.json` | a policy record (the 8 policy types) |
| `dcm-group.schema.json` | DCMGroups — tenants and profiles |
| `catalog-item.schema.json` | a Composite Service catalog item |
| `decision-record.schema.json` | a DecisionRecord (the substrate form of an ADR) |
| `audit-record` / `audit-leaf` / `commit-log-entry` | audit + tamper-evidence (Merkle, RFC 9162) |
| `function-capability-matrix.schema.json` | RBAC function matrix |

**Contracts (`contracts/`) — the wire behavior a peer must honor.** Load-bearing first: `provider-contract.md` (the provider interface + registration), `policy-contract.md` (policy evaluation), `identifier-scheme.md` (UUIDs/handles), `data-roles.md` (what data crosses the DCM→provider boundary), `event-catalog.md` + `time-and-clock.md` (events, clocks), `schema-sharing.md`, `error-model.md`, `capability-discovery.md`. The rest (`retry-semantics`, `rate-limit-and-backpressure`, `provider-callback-auth`, `storage-providers`, `information-providers*`, `cost-metering-linkage`, `data-store-contracts`) are scoped contracts referenced from those.

**Foundations (`foundations/`) — the concepts:** `four-states.md`, `data-model-core.md`, `layering-and-versioning.md`, `entity-type-families.md`. **Governance (`governance/`):** `accreditation-and-authorization-matrix.md`, `governance-matrix.md`, `authority-tier-model.md`, `credentials.md`. **Decisions (`docs/adr/`):** the *why* behind each of the above.

## 4. Scope, deferral, conformance

- **In scope / deferred / exit criteria:** [`registry/UDLM-1.0-SCOPE.md`](../registry/UDLM-1.0-SCOPE.md) — the normative definition. Deferred to post-1.0 (its §6): operational rehydration, `topology_capability`-as-reference, JIT credentials (§ TODOs), and other explicitly-listed items.
- **Ratification status:** [`docs/udlm-1.0-ratification-readiness.md`](udlm-1.0-ratification-readiness.md) — which ADRs are ready to ratify for the `0.1 → 1.0` tag.
- **Conformance bar:** [`docs/udlm-1.0-conformance-suite-plan.md`](udlm-1.0-conformance-suite-plan.md) and [`CONFORMANCE.md`](../CONFORMANCE.md) — what an implementation must pass to claim UDLM 1.0.

## 5. How to check your work (definition of done)

Three gates, all green before anything merges:

```
python3 registry/tools/validate.py        # every instance/provider/layer/accreditation validates;
                                           #   semantic checks (reference integrity, lineage, composite
                                           #   ordering) + the advisory change-impact map
python3 tests/validate_registry.py         # every Resource Type spec validates; $id↔version agreement;
                                           #   ADOPT-001 (every adopted standard is registered); UUID-v4
python3 tests/check_estate_tokens.py       # no private/estate tokens leaked into the public repo
```

`validate.py` loads JSON and YAML identically (same records, same schemas) and reads multi-document (`---`) files. A green run is the floor, not the ceiling — conformance (§4) is the release bar.

## 6. Reading order

1. This document, then [`README.md`](../README.md) and [`GLOSSARY.md`](../GLOSSARY.md).
2. `foundations/four-states.md` → `foundations/data-model-core.md` → `foundations/layering-and-versioning.md`.
3. `registry/UDLM-1.0-SCOPE.md` (what 1.0 is) → `docs/adr/` for the *why* of whatever you're touching.
4. The schema + contract for your area (§3), then write records and run the gates (§5).

The substrate is realization-neutral: implement to the schemas and contracts, not to DCM. If a decision feels like runtime behavior, apply the ADR-008 test — it probably belongs to DCM, not here.

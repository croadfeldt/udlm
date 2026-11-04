# UDLM Data Model — Core (normative)

Rulings **[D1]**..**[D8]** are normative; this document is the single normative statement of the UDLM data model.
**Authority rule:** where any other UDLM document disagrees with this one, THIS document wins and the other
document is defect-fixed to defer here. Each section lists the detailed documents it governs.

---

## 1. Identity & references

- Every entity — type spec, instance, policy, layer, group, tenant, audit record — carries an
  immutable **RFC 9562 v4 `uuid`** minted once at creation; **v7** only for declared
  time-ordered artifacts (event ids, audit leaves); all other versions prohibited.

- `handle` is ADVISORY human identity; mutable/rebindable. Every cross-entity reference is
  `{target_uuid: authoritative, target_handle: advisory}` — **never name alone**. Handle
  disagreement at resolution is drift, not failure.

- `correlation_ids` carry stable natural keys (smbios_uuid, mac, provider_id, …) for entity
  resolution across discovery sources: one real resource, one uuid.

- Boundary translation: external systems that reference by name (a control plane's catalog with
  name-keyed edges, for example) map name↔uuid at the Provider/catalog boundary;
  the external name is recorded as a `correlation_ids` entry (`scheme: provider_id`).

*Governs:* `docs/spec/contracts/identifier-scheme.md`, reference fields in both schemas.

## 2. Entities, types, instances

- Four families (ADR-027): **Resource** and **Process** — maintained state vs bounded
  execution — each with a **derived** Atomic/Composite shape (`has_constituents`, the coarse shape from the control plane's
  orchestration perspective, not a stored field). The other two are **Knowledge** (members defined in
  `docs/spec/foundations/knowledge-family.md` §4 — the one home for that list) and **Access** (`Identity`,
  `Escrow`, `Grouping` — the schema's `entity_type` set for the family), which do not carry the
  Atomic/Composite shape axis.

- A **Resource Type Specification** (validates against `registry/resource-type-spec.schema.json`)
  is the portable contract; an **instance** is stored as one record per lifecycle state (validates against
  `registry/state-record.schema.json`, ruling 071) and read as an entity view (`registry/entity-view.schema.json`). Type names are Tier-1 vendor-neutral
  `Base[.Type[.Provider]]` (single-segment for a Base, e.g. `Topology`; CLS-001) — and
  the record schema accepts exactly the same name grammar as the type schema.

- **Machine-validatable surface** — the model is only as solid as its schemas. Current: every record
  kind in `registry/*.schema.json`. **[D8] Committed program**, in
  priority order: (1) Tenant + grouping — **DONE** (the `Grouping` classes under
  `registry/classes/access/authorization/grouping/`, stored as state records; profiles via
  `registry/profile.schema.json`; `tenant_uuid` required on every instance; `registry/tools/validate.py`
  dispatches instances on `record_type`). (2) Catalog item — **DONE** (a catalog item is a provider Class:
  `registry/class.schema.json` carrying the `registry/composition.schema.json` constituents shape, +
  validate.py semantic checks; the application model — an application IS a composition — and the
  ADR-016 evidence; `docs/spec/foundations/template-composition-model.md` §1.2/§2.5). (3) Policy
  record + typed outputs **[DONE — registry/policy.schema.json; type-spec outputs are the
  referenceable typed binding surface, output-resolved by the validator]**. (4) Layer record **[DONE
  — registry/layer.schema.json]**. (5) Audit record + Commit Log entry **[DONE —
  registry/audit-record.schema.json, registry/audit-leaf.schema.json,
  registry/commit-log-entry.schema.json]**. (6) DecisionRecord **[DONE —
  registry/decision-record.schema.json; the WHY becomes a queryable, Data·Policy·Provider-decomposed
  record]**. (7) Process Resource **[DONE — the `process` execution axis on the realized record;
  execution_state separate from lifecycle_state per D7; validate.py enforces it on Process-family
  entities]**. **The D8 schema program is COMPLETE.** Until an artifact's schema exists, its prose
  definition is explicitly marked *pre-schema* and is not citable as "[enforced]".

*Governs:* `registry/SPEC-DESIGN-REQUIREMENTS.md`, `registry/classes/**`, `docs/spec/foundations/entity-types.md`.

## 3. Lifecycle — one enum, separate operational axes

- **`lifecycle_state` is the ONLY lifecycle enum**: `Intent → Requested → Realized ↔ Discovered` plus
  terminal `Decommissioned` (DEP-007's "retired" prose names the same phase). Two entry paths populate the
  same record. Greenfield is forward: consumer declares Intent; the control plane assembles Requested; **the
  Provider writes Realized — a receipt, never hand-authored**; discovery observes. Brownfield greening is
  reverse: Discovered-first/unclaimed → provider claim/adoption writes Realized, uuid preserved →
  Requested/Intent backfilled with `origin: backfilled|discovered_derived`.

- **[D7] Processes do not overload lifecycle_state.** Their run dynamics are a separate
  **`execution_state`** axis (`REQUESTED|INITIATED|EXECUTING|COMPLETED|FAILED|CANCELLED`). A
  Process entity still carries the universal lifecycle_state (a playbook that exists and is
  adopted is `Realized`/`Discovered` like anything else; each RUN moves execution_state).

- **Recovery and health are `status.conditions`, not lifecycle states.** The five recovery
  states (TIMEOUT_PENDING, LATE_REALIZATION_PENDING, INDETERMINATE_REALIZATION,
  COMPENSATION_IN_PROGRESS, COMPENSATION_FAILED) and composite DEGRADED are condition types on
  `status` — overlays on a lifecycle that never leaves the five values above.

- **[D6] Drift severity has ONE canonical enum:** `minor | significant | critical`. All other
  gradings (low/medium/high/critical, minor/moderate/…) are defects to be rewritten.

- **Discovered has a dual role** (ephemeral drift-snapshot stream AND durable per-uuid
  inventory of what exists, including unclaimed). **The durable-inventory role is EXEMPT from
  the retention ceiling** — retention windows apply to the snapshot stream only; the
  reconciled inventory record persists until claim or retirement.

*Governs:* `docs/spec/foundations/four-states.md`, `docs/spec/foundations/entity-types.md`,
`docs/spec/foundations/resource-service-entities.md` §6, ENTITY-VIEW.md population paths.

## 4. Relationships — typed data model, projectable to execution DAGs

- **Two tiers, one authoritative field each.** `edge_type` (closed, universal): `depends_on`
  (`strength: hard|soft`), `contained_by`, `binds_to` (consumes a typed output;
  `target_field`), `references` (informational). `relation` (domain tier): a name DECLARED by
  the pinned type (`relationships[].name`), adopted from standards (RFC 8343/8345, TOSCA),
  refining but never overriding its edge_type (REL rules, common-elements §9).

- **The `nature` axis** (constituent|operational|informational) is expressed by:
  constituents[] (constituent), edge_type ordering semantics (operational), `references`
  (informational). A peer or management concept is a declared relation name (under
  `references` and `depends_on` respectively), never an edge_type.

- **Composites** declare `constituents[]` (membership, ordering-neutral) and explicit
  `depends_on` edges (ordering). Ordering is always explicit, never inferred from membership.

- **Graphs are emergent and acyclic** over ordering edge_types (depends_on/contained_by/binds_to);
  forward topological order = provision/startup, **reverse = teardown/shutdown** — teardown is
  a first-class projection of the same edges. `soft` edges order but never block
  (degrade-don't-break, DEP-006).

- **Projection to an execution DAG.** An execution engine's graph is typically a single untyped
  "must-come-before" DAG: name-referenced, hard-only, with no teardown order. The UDLM model projects
  LOSSLESSLY DOWN onto such a DAG: `depends_on(hard)` → a prerequisite edge;
  `binds_to{target_field}` → the engine's declared form of output wiring;
  `contained_by` → an ordering edge at provision, plus the containment fact a plain DAG cannot express.
  `soft` edges and `references` drop out of the execution DAG by design. The reverse projection is
  lossy — which is the argument for keeping the typed model as the data model and treating execution
  DAGs as compiled artifacts.

*Governs:* `docs/spec/foundations/entity-relationships.md`, `docs/spec/foundations/service-dependencies.md`,
`registry/common-elements.md` §7/§7a/§9, both schemas' relationship surfaces.

## 5. Tenancy & grouping

- **[D3] Every instance carries `tenant_uuid` (schema-required).** TEN-001/003 become
  schema-enforceable, not prose. Existing stores migrate by minting their tenants and
  backfilling (the estate: one tenant per lab).
- Tenants are groupings. **the grouping vocabulary is ONE closed set** — the universal-groups closed
  set (tenant_boundary, resource_grouping, …, plus cross_tenant_authorization added to the
  table); resource-grouping's `dcm_default|custom` becomes `group_subclass`. One membership
  record shape (the universal-groups form: added_at/added_by/valid_from/membership_status).

*Governs:* `docs/spec/foundations/resource-grouping.md`, `docs/spec/foundations/universal-groups.md`, DCM ADR-014 seam.

## 6. Time, attribution, and audit-grade recording

- All instants are **RFC 3339 normalized to UTC (`Z`)**, pattern-enforced (`format:` alone is
  not enforcement); snapshots carry **`time_source`** (required on realized/discovered) and
  **`origin`** (declared | discovered_derived | backfilled). No fabricated precision.

- **E4 field-level provenance holds in every profile** (homelab = derivable-carrier/git;
  standard/prod = materialized; fsi/sovereign = + audit chain). Provenance `source.kind`
  vocabulary: `layer | policy | actor | provider | discovery | rehydration | override` (`override`
  records a DCM ADR-013 override; `discovery` and `rehydration` record those writes).
  **Home (ADR-059):** the modification history lives in the audit record family (sealed,
  `udlm_provenance` facet), never on the working record — the record makes state claims
  only. The in-record provenance block (`state-record.schema.json` `$defs/provenance`) is a
  convenience copy, not citable as lineage.

- **[D2] Audit integrity is the RFC 9162 Merkle model** (AUD-006; DCM ADR-010) — per-leaf
  signatures, signed tree heads. The "linear SHA-256 chain" wording elsewhere is a defect.

- **[D1] Lifecycle data stores are defined by CONTRACT, not technology** (sovereignty and
  tenancy make store choice a policy outcome). Four
  normative store contracts, each with invariants any conforming store must satisfy. **Commit
  Log** (synchronous, consensus-durable before success — AUD-001). **State Store** (immutable
  snapshots, point-in-time by uuid, per-dot-path provenance, retention, tenancy isolation,
  residency placement). **Audit Store** (append-only, RFC 9162 Merkle — an app-level
  construction that works above any store — AUD-008 query dimensions, WORM-capable retention for
  fsi). **Discovered stream** (rolling snapshots, retention windows). A deployment BINDS each
  contract to a conforming store via profile + sovereignty/tenancy policy, and the binding is
  declared and auditable (storage-provider records,
  `docs/spec/contracts/data-store-contracts.md`). **PostgreSQL is the reference implementation**
  satisfying all four contracts in one store at `standard`/`prod`; **git is a conforming
  `homelab`-profile carrier** (derivable provenance). `fsi`/`sovereign` MAY — and where
  isolation or residency policy requires, MUST — split stores per tenant/zone, use WORM audit
  tiers, embedded stores for disconnected/day-0 sites, or accredited substitutes. Conformance is
  measured against the contract, never the brand. Tenancy isolation is profile-keyed:
  shared-schema row-level security (`standard`) → schema/database-per-tenant (`fsi`) →
  store-instance-per-tenant/zone (`sovereign`).

*Governs:* `registry/common-elements.md` §8, `docs/spec/contracts/universal-audit.md`,
`docs/spec/contracts/audit-provenance-observability.md`, `docs/spec/contracts/event-catalog.md` (envelope
timestamps RFC 3339 'Z'; `event_uuid` = v7).

## 7. Canonical enum registry

One definition each; everything else defers here:

| Enum | Canonical values | Home |
|---|---|---|
| family | Resource, Process, Knowledge, Access | entity-type-families §4 (ADR-027) |
| entity_type (Knowledge/Access discriminator) | Knowledge: per knowledge-family §4 (the one home for the member list) · Access: Identity, Escrow, Grouping | knowledge-family §4 / schema `family` allOf |
| has_constituents (derived shape) | Atomic, Composite — Resource & Process only, *derived* not stored | entity-types §2.2 (ADR-027) |
| lifecycle_state | Intent, Requested, Realized, Discovered, Decommissioned | §3 |
| execution_state (Process) | REQUESTED, INITIATED, EXECUTING, COMPLETED, FAILED, CANCELLED | §3 [D7] |
| drift severity | minor, significant, critical | §3 [D6] |
| edge_type | depends_on, contained_by, binds_to, references | §4 |
| depends_on strength | hard, soft | §4 |
| snapshot origin | declared, discovered_derived, backfilled | §6 |
| provenance source.kind | layer, policy, actor, provider, discovery, rehydration, override | §6 |
| stake strength | required, preferred, optional | ownership doc (events defer) |
| record kind | universal-groups closed set + cross_tenant_authorization | §5 |
| Provider model | capability declarations (ADR-PROV-002), not a fixed type count | docs/spec/contracts/provider-contract.md **[D5]** |

## 8. Conformance — the honest enforcement ledger

A rule may claim **[enforced]** only if a running validator checks it. Current honest state: schema
validation + $id/version cross-checks + ADOPT-001 + PII-001 run in registry CI. Schema validation
covers the type spec, state-record and entity-view (incl. required `tenant_uuid` [D3]), provider
matrices, groupings as state records of the `Grouping` classes (`Grouping.Tenant` with its required
isolation obligation, `Grouping.Authorization` with its grant fields), and profiles via
`registry/profile.schema.json`. It also covers compositions via `registry/composition.schema.json` (incl. required
`tenant_uuid`), plus validate.py semantic checks: component_id uniqueness, sibling
depends_on/binding resolution, depends_on cycle rejection, and binding⊆depends_on ordering. Also
enforced, **on new findings** only: uuid v4-nibble, snake_case key patterns, relationship-name
coverage, and the PVD portable-value scan (`tests/check_portable_values.py`, `PVD-001`). The
pre-existing set is triaged in `tests/portable-values-baseline.yaml` at the registry layer — tracked
defects, not claims. Semver compatibility is enforced: `tests/ci_compat_gate.py` runs
`compat-check.py` on every changed spec against `origin/main`. Every "[enforced]" marker elsewhere is audited against this
ledger.

**The refusal contract is specification, not enforcement.** The rules governing what a refusal must be —
typed, actionable, non-leaking, auditable — are in `docs/spec/contracts/error-model.md` §6a. Those
rules, and the per-surface rules that apply them (`XTA-006`/`XTA-007`, `GMX-011`–`GMX-013`,
`CPX-013`/`CPX-014`, `CMP-009`, `PRV-011`, `REG-011`–`REG-016`), describe behavior at request, dispatch,
and promotion time. None of it is checked by a validator in this repository, and none of it claims
`[enforced]`. Two of the registry-plane rules generalize checks that *do* run on the flat-spec plane
today — version sufficiency (`tests/ci_compat_gate.py`) and version honesty on consumer manifests
(`tests/check_consumer_conformance.py`). The class-plane gates additionally wait on a class-plane compat
classifier that does not exist yet: class artifacts and their schema have landed (`registry/classes/`,
`registry/class.schema.json` — ADR-061), but compatibility is still priced only on the generated
flat-spec plane. Listing the gap here is the point of the ledger: a written refusal is a contract, and
calling it enforcement would be the exact dishonesty this section exists to prevent.

---

*Defect-fix sweeps (rule-ID renumbering, enum rewrites, casing, stale citations) are tracked
in the 2026-07-06 consistency-review fix plan and land as conformance-to-core changes.*

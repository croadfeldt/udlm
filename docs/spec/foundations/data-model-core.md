# UDLM Data Model — Core (normative)

Rulings **[D1]**..**[D8]** are normative; this document is the single normative statement of
the UDLM data model. **Authority rule:** where any other UDLM document disagrees with this one, THIS document wins
and the other document is defect-fixed to defer here (the 2026-07-06 consistency review found
5 colliding rule-ID families, 4 drift-severity enums, and 3 relationship vocabularies —
precisely because no single normative core existed). Each section lists the detailed documents
it governs.

---

## 1. Identity & references

- Every entity — type spec, instance, policy, layer, group, tenant, audit record — carries an
  immutable **RFC 9562 v4 `uuid`** minted once at creation; **v7** only for declared
  time-ordered artifacts (event ids, audit leaves); all other versions prohibited.
- `handle` is ADVISORY human identity; mutable/rebindable. Every cross-entity reference is
  `{target_uuid: authoritative, target_handle: advisory}` — **never name alone**. Handle
  disagreement at resolution is drift, not failure.
- `correlation_ids` carry stable natural keys (smbios-uuid, mac, provider-id, …) for entity
  resolution across discovery sources: one real resource, one uuid.
- Boundary translation: external systems that reference by name (e.g. the DCM control-plane
  catalog's `requires_resources` name-edges) map name↔uuid at the Provider/catalog boundary;
  the external name is recorded as a `correlation_ids` entry (`scheme: provider-id`).

*Governs:* `docs/spec/contracts/identifier-scheme.md`, reference fields in both schemas, REF-001/002.

## 2. Entities, types, instances

- Four families (ADR-027): **Resource** and **Process** — maintained state vs bounded
  execution — each with a **derived** Atomic/Composite shape (`has_constituents`, the coarse shape from DCM's
  orchestration perspective, not a stored field); plus **Knowledge** (members defined in
  `docs/spec/foundations/knowledge-family.md` §4 — the one home for that list) and **Access** (`Identity`),
  which do not carry the Atomic/Composite shape axis.
- A **Resource Type Specification** (validates against `registry/resource-type-spec.schema.json`)
  is the portable contract; an **instance** is a realized-entity record (validates against
  `registry/realized-entity.schema.json`). Type names are Tier-1 vendor-neutral
  `Category.Type` (single-segment permitted for cross-cutting types, e.g. `Topology`) — and
  the instance schema accepts exactly the same name grammar as the type schema.
- **Machine-validatable surface** — the model is only as solid as its schemas. Current: type
  spec, realized-entity, provider-adopted-standards, profile. **[D8] Committed program**, in
  priority order: (1) Tenant + grouping — **DONE** (`registry/profile.schema.json` / `Grouping` + required
  instance `tenant_uuid`; `registry/tools/validate.py` dispatches instances on `record_type`),
  (2) catalog item — **DONE** (`registry/catalog-item.schema.json`, dispatched on
  `record_type: catalog_item` + validate.py semantic checks; the application model — an
  application IS a Composite catalog item — and the DCM ADR-016 evidence;
  `docs/spec/foundations/template-composition-model.md` §1.4/§2.5), (3) policy record + typed outputs **[DONE — registry/policy.schema.json; type-spec outputs are the referenceable typed binding surface, output-resolved by the validator]**, (4) layer record **[DONE — registry/layer.schema.json]**, (5) audit record +
  Commit Log entry, (6) DecisionRecord **[DONE — registry/decision-record.schema.json; the WHY becomes a queryable, Data·Policy·Provider-decomposed record]**, (7) Process Resource **[DONE — the `process` execution axis on realized-entity; execution_state separate from lifecycle_state per D7; validate.py enforces it on Process-family entities]**. **The D8 schema program is COMPLETE.** Until an artifact's schema
  exists, its prose definition is explicitly marked *pre-schema* and is not citable as
  "[enforced]".

*Governs:* `registry/SPEC-DESIGN-REQUIREMENTS.md`, `entities/*`, `docs/spec/foundations/entity-types.md`.

## 3. Lifecycle — one enum, separate operational axes

- **`lifecycle_state` is the ONLY lifecycle enum**: `Intent → Requested → Realized ↔ Discovered`
  plus terminal `Decommissioned` (DEP-007's "retired" prose names the same phase). Two entry
  paths populate the same record: greenfield (forward: consumer declares Intent; DCM assembles
  Requested; **the Provider writes Realized — a receipt, never hand-authored**; discovery
  observes) and brownfield greening (reverse: Discovered-first/unclaimed → provider
  claim/adoption writes Realized, uuid preserved → Requested/Intent backfilled with
  `origin: backfilled|discovered-derived`).
- **[D7] Processes do not overload lifecycle_state.** Their run dynamics are a separate
  **`execution_state`** axis (`REQUESTED|INITIATED|EXECUTING|COMPLETED|FAILED|CANCELLED`); a
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
  the RHY-008 retention ceiling** — retention windows apply to the snapshot stream only; the
  reconciled inventory record persists until claim or retirement.

*Governs:* `docs/spec/foundations/four-states.md`, `docs/spec/foundations/entity-types.md`,
`docs/spec/foundations/resource-service-entities.md` §6, REALIZED-ENTITY.md population paths.

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
- **Projection to the DCM execution DAG** (per the 2026-07-06 dcm-project comparison — their
  merged model is a single untyped "must-come-before" DAG from `requires_resources` +
  CEL-inferred edges, name-referenced, hard-only, with teardown unspecified and runtime
  execution TODO): the UDLM model projects LOSSLESSLY DOWN onto theirs —
  `depends_on(hard)` → `requires_resources`; `binds_to{target_field}` → the declared form of
  their CEL output wiring (`${producer.output}`); `contained_by` → an ordering edge at
  provision, plus the containment fact they cannot express; `soft` edges and `references`
  drop out of the execution DAG by design. The reverse projection is lossy — which is the
  argument for keeping the typed model as the data model and treating execution DAGs as
  compiled artifacts. UDLM's reverse-topological teardown and typed-outputs formalization are
  offered upstream as the fill for their two explicit gaps.

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
  **`origin`** (declared | discovered-derived | backfilled). No fabricated precision.
- **E4 field-level provenance holds in every profile** (homelab = derivable-carrier/git;
  standard/prod = materialized; fsi/sovereign = + audit chain). Provenance `source.kind`
  vocabulary: `layer | policy | actor | provider | discovery | rehydration | override` (the
  last three added so DCM ADR-013 overrides and discovery/rehydration writes are recordable).
  **Home (ADR-059):** the modification history lives in the audit/OL record family (sealed
  seals, `udlm_provenance` facet), never on the working record — the record makes state claims
  only; the in-record #191 provenance block migrates there (pending supersession, executed with
  the receipt-schema phase).
- **[D2] Audit integrity is the RFC 9162 Merkle model** (AUD-006, ADR-010) — per-leaf
  signatures, signed tree heads. The "linear SHA-256 chain" wording elsewhere is a defect.
- **[D1] Lifecycle data stores are defined by CONTRACT, not technology** (revised 2026-07-06,
  maintainer ruling — sovereignty and tenancy make store choice a policy outcome). Four
  normative store contracts, each with invariants any conforming store must satisfy:
  **Commit Log** (synchronous, consensus-durable before success — AUD-001), **State Store**
  (immutable snapshots, point-in-time by uuid, per-dot-path provenance, retention, tenancy
  isolation, residency placement), **Audit Store** (append-only, RFC 9162 Merkle — an
  app-level construction that works above any store — AUD-008 query dimensions, WORM-capable
  retention for fsi), **Discovered stream** (rolling snapshots, RHY-008 windows). A deployment
  BINDS each contract to a conforming store via profile + sovereignty/tenancy policy, and the
  binding is declared and auditable (storage-provider records,
  `docs/spec/contracts/data-store-contracts.md`). **PostgreSQL is the reference implementation**
  satisfying all four contracts in one store at `standard`/`prod`; **git is a conforming
  `homelab`-profile carrier** (derivable provenance); `fsi`/`sovereign` MAY — and where
  isolation or residency policy requires, MUST — split stores per tenant/zone, use WORM audit
  tiers, embedded stores for disconnected/day-0 sites, or accredited substitutes. Conformance
  is measured against the contract, never the brand. Tenancy isolation is profile-keyed:
  shared-schema RLS (`standard`) → schema/database-per-tenant (`fsi`) →
  store-instance-per-tenant/zone (`sovereign`).

*Governs:* `registry/common-elements.md` §8, `docs/spec/contracts/universal-audit.md`,
`docs/spec/contracts/audit-provenance-observability.md`, `docs/spec/contracts/event-catalog.md` (envelope
timestamps RFC 3339 'Z'; `event_uuid` = v7).

## 7. Canonical enum registry

One definition each; everything else defers here:

| Enum | Canonical values | Home |
|---|---|---|
| family | Resource, Process, Knowledge, Access | entity-type-families §4 (ADR-027) |
| entity_type (Knowledge/Access discriminator) | Knowledge: per knowledge-family §4 (the one home for the member list) · Access: Identity | knowledge-family §4 / schema `family` allOf |
| has_constituents (derived shape) | Atomic, Composite — Resource & Process only, *derived* not stored | entity-types §2.2 (ADR-027) |
| lifecycle_state | Intent, Requested, Realized, Discovered, Decommissioned | §3 |
| execution_state (Process) | REQUESTED, INITIATED, EXECUTING, COMPLETED, FAILED, CANCELLED | §3 [D7] |
| drift severity | minor, significant, critical | §3 [D6] |
| edge_type | depends_on, contained_by, binds_to, references | §4 |
| depends_on strength | hard, soft | §4 |
| snapshot origin | declared, discovered-derived, backfilled | §6 |
| provenance source.kind | layer, policy, actor, provider, discovery, rehydration, override | §6 |
| stake strength | required, preferred, optional | ownership doc (events defer) |
| record kind | universal-groups closed set + cross_tenant_authorization | §5 |
| Provider model | capability declarations (ADR-005), not a fixed type count | docs/spec/contracts/provider-contract.md **[D5]** |

## 8. Conformance — the honest enforcement ledger

A rule may claim **[enforced]** only if a running validator checks it. Current honest state:
schema validation (type spec, realized-entity — incl. required `tenant_uuid` [D3] — provider
matrices, grouping via `registry/profile.schema.json` / `Grouping` with per-class conditionals:
tenant `ownership`/`isolation_level`/`membership_policy.exclusive: true`, cross-tenant-auth
grant fields, and Composite Service catalog items via `registry/catalog-item.schema.json` —
incl. required `tenant_uuid` — plus validate.py semantic checks: component_id uniqueness,
sibling depends_on/binding resolution, depends_on cycle rejection, and binding⊆depends_on
ordering) + $id/version cross-checks + ADOPT-001 + PII-001 (registry CI); uuid
v4-nibble, snake_case key patterns, relationship-name coverage, and the PVD portable-value scan
(`tests/check_portable_values.py` — planned, not yet landed) are **NOT yet enforced** at the registry layer (semver compat IS now enforced — tests/ci_compat_gate.py runs compat-check on every changed spec vs origin/main) — tracked defects, not claims. Every
"[enforced]" marker elsewhere is audited against this ledger.

**The refusal contract is specification, not enforcement.** The rules governing what a refusal
must be — typed, actionable, non-leaking, auditable (`docs/spec/contracts/error-model.md` §6a) — and the
per-surface rules that apply it (`XTA-006`/`XTA-007`, `GMX-011`–`GMX-013`, `CPX-013`/`CPX-014`,
`CMP-009`, `PRV-011`, `REG-011`–`REG-016`) describe behavior at request, dispatch, and promotion
time. None of it is checked by a validator in this repository, and none of it claims
`[enforced]`. Two of the registry-plane rules generalize checks that *do* run on the flat-spec
plane today — version sufficiency (`tests/ci_compat_gate.py`) and version honesty on consumer
manifests (`tests/check_consumer_conformance.py`) — and the class-plane gates additionally wait
on a class-plane compat classifier that does not exist yet: class artifacts and their schema have
landed (`registry/classes/`, `registry/class.schema.json` — ADR-061), but compatibility is still
priced only on the generated flat-spec plane. Listing the gap here is the point
of the ledger: a written refusal is a contract, and calling it enforcement would be the exact
dishonesty this section exists to prevent.

---

*Defect-fix sweeps (rule-ID renumbering, enum rewrites, casing, stale citations) are tracked
in the 2026-07-06 consistency-review fix plan and land as conformance-to-core changes.*

# UDLM Spec Design Requirements

The rubric every UDLM **Resource Type Specification** is designed to. **Hard constraints** are
normative (MUST); those marked **[enforced]** are checked by `tools/validate.py` /
`tools/compat-check.py` and should run in CI. **Design principles** are review discipline (SHOULD).
Each hard constraint cites the UDLM contract it derives from.

## Hard constraints (MUST)

### Format & validity
1. **JSON Schema 2020-12** is the normative model — the format for all entity-type definitions
   (`contracts/schema-sharing.md`).
2. Authorable in **JSON or YAML**, 1:1 — same document, same meta-schema. **[enforced]**
3. **Valid-by-construction** — validates against `resource-type-spec.schema.json` or it is not a
   conformant spec. **[enforced]**
4. **Structural schema** — every field typed, `additionalProperties` controlled; no untyped blobs.

### Identity & naming
5. **UUIDv4** identity, immutable for the type's life; Handles are mutable/rebindable, References are
   typed cross-doc pointers (`contracts/identifier-scheme.md`). **[enforced: format]**
6. **Vendor-neutral `Category.Type` name**, e.g. `Compute.VirtualMachine`
   (`entities/resource-type-hierarchy.md`). Full conventions — tiered namespaces (Tier-1 `Category.Type`
   vendor-neutral / Tier-2 `Vendor.Type`), when to add a category, field/output/file naming, and the
   *name-to-an-existing-standard-before-inventing* rule — live in **`registry/naming-conventions.md`**.
   **[enforced: pattern]**

### Versioning — two axes
7. **`conforms_to: udlm/<MAJOR.MINOR>`** — SPEC-axis binding (apiVersion); same MAJOR = wire-compatible
   (`CONFORMANCE.md` §9). **[enforced: pattern]**
8. **`version: MAJOR.MINOR.REVISION`** — ENTITY axis; immutable once published; any change publishes a
   new version (`foundations/layering-and-versioning.md`). **[enforced: pattern]**
9. **Semver semantics**: additive → MINOR, breaking → MAJOR, docs → REVISION. **[enforced: compat-check]**
10. A **MAJOR** bump deprecates the predecessor and MUST carry `migration_guidance`; a deprecation
    window precedes retirement (universal deprecation model + K8s deprecation policy).
11. **Version-pinned references** — profiles (E1) and realized instances (E5) pin the exact version used.

### Lifecycle & ownership
12. Conforms to the **four states** Intent → Requested → Realized → Discovered (`foundations/four-states.md`).
13. **`spec` = desired state** (Intent/Requested, consumer-authored); **`outputs` = observed state**
    (Realized/Discovered, provider-authored). Never blurred (the K8s spec/status discipline).
14. **Realization is the authoritative system of record** for realized data — the basis of sovereignty
    and audit (`entities/resource-service-entities.md`).

### Portability & provider-neutrality
15. The spec is the contract **any** provider of the type MUST satisfy; providers
    naturalize → realize → denaturalize (`contracts/provider-contract.md`).
16. **Any deviation from full portability MUST be explicitly declared** via `portability`. **[enforced: enum]**
17. **No provider-specific (vendor-exclusive) data in the universal spec** — those ride declared
    extension points (`portability` + `provider_hints` / the provider surface). **This binds adoption
    too:** a type MUST NOT pull a standard's *vendor-exclusive* elements into its portable spec. A
    standard that is itself vendor-exclusive is adopted only at the provider/extension surface
    (`portability: provider-specific`), never in the base contract — the portable spec stays the
    neutral subset every provider can satisfy.

### Relationships
18. Relationships are **first-class and typed** (`depends_on`/`binds_to`/`references`/`contained_by`),
    target **resource types** (never provider-specific refs), and form **acyclic** composite DAGs
    (`entities/service-dependencies.md`, `entities/composite-service-model.md`). **[enforced: shape]**

### Interop & data discipline
19. **Wire-compatible** — any conformant peer can deserialize, scope-resolve, reference, and validate
    it; independent extensions stay interoperable via the schema-sharing protocol
    (`contracts/identifier-scheme.md`, `contracts/schema-sharing.md`).
20. **Data, not logic** — a spec carries values + declarative constraints; *executable* rules are
    Policy, *static* values are Layers (`foundations/layering-and-versioning.md` §1a).
21. **No embedded expressions** — a spec carries *declarative* constraints only (JSON Schema
    `if/then` · `dependentSchemas` · `enum` · bounds + markers like `createOnly`); it embeds **no**
    expression language or executable behavior. Transformation/enrichment is Policy, applied by DCM;
    the contract layer stays deterministic + reproducible (`design-principles/core-tenets.md` T2/T3).
    **Computation is relocated, not banned.** When a computed binding *is* needed (e.g. a CEL
    expression combining declared outputs), it is a **Transformation Policy evaluated by DCM's policy
    engine** — never embedded in the portable data. It is safe *iff*: (a) the evaluator is
    **pure/deterministic** (sandboxed CEL — no I/O, clock, or randomness), so it is reproducible from
    the immutable record; (b) its inputs are **declared typed bindings** (governable edges); and (c) the
    **policy engine records the evaluation** (`expression@version` + resolved inputs + output), so the
    computed field's provenance points to the policy and every input edge. The policy-evaluation seam is
    already the audit/provenance capture point (DCM ADR-006/010) — computation stays expressive while the
    portable data stays declarative and the result stays auditable + provenanced.
    Two further controls bound it: **(d) per-field opt-in** — a field is a valid CEL target only if its
    definition declares **`cel_permitted: true`** (default **false**; a declarative field marker alongside
    `createOnly`/`immutable`/`sensitive`). Producers of types/layers/catalog items decide which fields
    accept computed bindings — computation is opt-in (the *simple-common-case* principle); the policy
    engine rejects a CEL op targeting a non-permitted field. **(e) Uncovered-computed-field notification**
    — if a CEL op sets a field that **no policy reads or constrains**, the result is *ungoverned*
    ("unbounded"): the engine emits an **`uncovered_computed_field`** observation (recorded, pairs with
    provenance) and the **DCM operational profile** sets the action (notify → warn → block; sovereign/
    critical → block). Together: producers gate *which* fields may be computed; the platform flags *when*
    a computed field is ungoverned.
    **Field markers are contract data — policy governs and gates them, but never rewrites them.** A
    field's markers (`cel_permitted`, `immutable`, `sensitive`, …) are part of the contract: their
    *effective* value is the base definition **narrowed** by declarative layers (constraint profiles / org
    layers — E1 *narrow-never-widen*, recorded with provenance), so it is reproducible (T1/T3). A policy
    MUST NOT flip a flag in place; it MAY (i) **authorize/govern** who narrows it, and (ii) add a runtime
    **gate on the operation** (e.g. incident-mode → deny all CEL; a tenant → no computed fields), recorded
    as a decision. **Direction:** *tightening* (e.g. `cel_permitted` true→false) is allowed via a narrowing
    layer or a runtime gate; *loosening* (false→true — permitting what a producer disallowed) requires a
    deliberate contract/version change, never a policy or overlay (preserves producer control).

### Adopted standards — provenance & licensing
22. **Source provenance** — every type or field whose vocabulary is **adopted** from an external
    standard (the *adopt* disposition, `design-principles/adopted-standards.md`) MUST record the
    source: the standard's name, version/edition, and canonical URL, in the type's `adopts[]` reference
    (the `adopted_standard_ref` in `registry/resource-type-spec.schema.json`) or a field-level
    `x-standard` pointer. (A provider separately declares which standard *versions* it can emit/consume
    via `registry/provider-adopted-standards.schema.json` — a different concern.) A definition that
    borrows elements with no recorded source is invalid.
23. **License compatibility** — before adopting, the source's license MUST be checked against the
    UDLM project license (Apache-2.0) and the verdict recorded with the source. **Referencing** a
    standard's *vocabulary* (field/element names — facts, not copyrightable) is always permitted,
    whatever the source license. **Copying** a source's schema text, enum bodies, or normative prose
    into the UDLM tree (an *absorb*) is permitted ONLY from an Apache-2.0-compatible license;
    copyleft / file-scoped sources (GPL, LGPL, MPL) MAY be **referenced by name** but their text or
    files MUST NOT be vendored into UDLM (`governance/registry-governance.md`, IP hygiene). This is
    why the disposition default is *adopt-by-reference*: it is both schema-rev-decoupled **and**
    license-clean.
23a. **Adopt-by-reference casing — foreign names never become live keys.** Adopting a standard's
    vocabulary means *referencing* its names, not *minting* them as resource keys. The **live field name
    is always the native (`snake_case`) form** (`serial_number`); the adopted source name — whatever its
    casing (Redfish PascalCase `SerialNumber`, Metal3 camelCase `serialNumber`) — is recorded as a
    **metadata value**, never a key: `adopts[].standard_name`, a field-level `x-standard` pointer, or
    `aliases[]`. Foreign casing MAY appear ONLY as such a metadata value, as an enum/string *value*, or
    inside an explicitly-opaque extension/raw blob (`provider_hints`, `x-…`, discovered-raw) — **never**
    as a typed key in the resource body. This keeps the canonical wire (and the AEP-bound DCM API it
    rides) uniformly `snake_case` even though the registry adopts many differently-cased standards
    (`registry/naming-conventions.md` §4 carve-outs). A type that mints a foreign-cased live key violates
    both §25 and this rule.

### Cross-type consistency
24. **Shared concepts use shared shapes** — a concept that recurs across types (compute resources
    cpu/memory, storage capacity, network CIDR / IP family, identity references, quantities,
    timestamps, status conditions) MUST reuse the registry's **canonical common-element definitions**
    (`registry/common-elements.md`), not be re-expressed per type. New or revised types are checked
    against the common-element catalog; an unjustified divergence is a review finding.
25. **Consistent naming & units** — field names are `snake_case` (`registry/naming-conventions.md` §4:
    canonical-data-model + AEP-conformance forces one casing; lowercased initialisms, e.g. `pod_cidr`);
    physical quantities carry an explicit unit via the canonical `Quantity` pattern (never a bare number
    whose unit is implied by the field name); timestamps are RFC 3339; enums use the canonical token set.
    New types are swept against the existing registry for naming/unit drift before publication.

### Component granularity (entity vs data element)
26. **A physical component (DIMM, disk, NIC, GPU, CPU) is representable BOTH ways, and the parent
    always carries the rollup.** The containing resource (e.g. `Compute.BareMetalInstance`) MUST carry
    the **aggregate as a data element** (`memory.size`, `cpu.count`) — the base contract never depends
    on components being modeled. A component MAY *also* be a **first-class entity** (`Hardware.*`,
    `contained_by` the parent) for independent tracking (serial, slot, firmware, RMA, lifecycle),
    governed by **`composition_visibility`** (`opaque|transparent|selective`,
    `entities/service-dependencies.md` §11d): `opaque` → rollup only; `transparent`/`selective` →
    components are entities too. When components are modeled, the parent rollup is the **reconciled
    aggregate** of the contained components; a mismatch is **drift** (surfaced, not silently merged).
    Component entities are additive (MINOR) — never required for the portable contract.

27. **Instances of the same type MUST be individually distinguishable.** When a parent holds multiple
    components of one type — two identical 32 GB DIMMs, eight same-model drives — each instance MUST
    carry enough identity to tell them apart, even when type, size, and use are identical. Use the
    canonical `Identity` element (`registry/common-elements.md`): **`location`** (physical position
    within the parent — DIMM slot `P1-DIMMA1`, drive bay `Bay 7`, PCIe slot — unique within the parent,
    stable across reboots) and **`serial_number`**/**`wwn`** (globally unique hardware identity, survives
    a move to another parent). A semantic **`role`/`usage`** field distinguishes same-model components
    by *purpose* (a drive as `boot` vs `ceph-osd`; memory as `system` vs `persistent`). The entity's own
    UUID is its UDLM identity; `location`/`serial_number`/`role` are the **discriminators** that bind that
    UUID to one physical instance and make "same type, different unit" and "same use, different serial"
    both expressible. The same rule applies inline (the rollup's `modules[]`/`disks[]` arrays MUST key
    each element by `location` or `serial_number`, never by array position alone). Grounded in Redfish
    (`Memory.SerialNumber`+`DeviceLocator`, `Drive.SerialNumber`+`WWN`+`PhysicalLocation`) and Metal3
    (`storage[].{name,serial_number,wwn}`, `nics[].mac`).

### Lifecycle entry — raw & unallocated resources
28. **A type MUST support a "raw" existence: Discovered state populated, no Intent.** A resource that
    physically exists but has not been allocated — a freshly racked server, a brownfield import, a spare
    drive on the shelf — MUST be representable for **inventory and tracking** with only its Discovered
    state populated and **no Intent/allocation** (`foundations/four-states.md` §2.4). Such a resource
    carries an **availability** lifecycle state (canonical `lifecycle_state`, e.g.
    `available|allocated|retired`; adopts Metal3 `provisioning.state: available`) marking it
    unallocated. It is later **adopted** — an Intent is attached (allocation / brownfield ingestion),
    entering the managed lifecycle — and adoption MUST **preserve the entity UUID** (four-states §3),
    so all inventory history accrues to the same entity. "Ingest raw, append changes later" is therefore
    the discovered-first lifecycle entry, the peer of intent-first (declare → realize). A type whose
    schema *requires* Intent fields to instantiate violates this rule.

### Decision decomposition — the three abstractions
29. **Every type and every decision is decomposed across the three foundational abstractions —
    `Data · Policy · Provider`** (DCM ADR-002; the UDLM Data⇄Policy boundary, `design-principles/core-tenets.md`).
    A capability is only fully scoped when each is named: **Data** = what UDLM models/holds (types,
    common-elements, served overlays); **Policy** = what DCM decides/computes/governs (the rules,
    matching, gating); **Provider** = what a provider *declares as possible* and the *mechanism it
    executes* (unmodeled). A DecisionRecord/ADR MUST carry a **Data · Policy · Provider** section (or
    explicitly state "n/a, because…" for any that genuinely doesn't apply). This prevents modeling a
    requirement as data with no policy to consume it, or a mechanism with no provider to declare it. It
    is foundational across UDLM, DCM, and (where applicable) DAV.

30. **Universal identity is RFC 9562 UUID — v4 for identity, v7 for time-ordered artifacts,
    everything else prohibited** (`contracts/identifier-scheme.md` §2.1, normative). Every entity,
    type spec, instance, policy, provider, and request carries an immutable v4 uuid minted once at
    creation (CSPRNG) and never reused (§5). Every cross-entity reference is
    `{uuid: authoritative, handle: advisory}` — never name alone (foundations/context-and-purpose.md
    §3). Validators MUST check version nibble + variant bits at ingest/authoring
    (estate CI and `tests/validate_registry.py` do).

31. **Every standards decision is registered — what, why, where, when, who**
    (`registry/standards-adoption-register.md`, normative). Any standard a spec adopts, absorbs
    a pattern from, retires, or deliberately REJECTS gets a DecisionRecord-shaped register
    entry: the exact `adopts[].standard` strings it covers, the rationale *including
    alternatives considered*, the git-derived adoption instant (common-elements §8 — no
    fabricated precision), the decider, where it is used, and the license verdict. An
    `adopts[]` entry whose standard string has no register entry fails CI (`ADOPT-001`,
    `tests/validate_registry.py`). **[enforced]** Rejections are first-class: a standard
    evaluated and not adopted is recorded with the same rigor, so the next reader doesn't
    re-run the evaluation.

32. **Tenancy is schema-enforced.** Every realized-entity instance carries a required
    `tenant_uuid` — the uuid of a `tenant_boundary` DCMGroup validating against
    `registry/dcm-group.schema.json` (TEN-001/TEN-003, `entities/resource-grouping.md` §2.2;
    `foundations/data-model-core.md` §5 [D3]). **[enforced]** (`registry/tools/validate.py`;
    referential existence of the tenant is a store-level check, not a schema one).

## Design principles (SHOULD)
- **Minimal core, extensible at the edges** — don't over-model; add types via schema-sharing.
- **Decouple the model from any runtime/controller** — the model outlives the engine that realizes it.
- **Typed outputs are the only cross-entity binding surface** (E2); flag `sensitive` outputs.
- **Profiles narrow, never widen** the base contract (E1).
- **Field-level provenance** — every assembled field records the layer/policy that set it (E4).
- **Reproducible** — spec + inputs deterministically yields the same Requested/effective state.
- **One concept per field**; cross-field/conditional constraints expressed **declaratively** in JSON
  Schema (`if`/`then`, `dependentSchemas`, `enum`), never an embedded expression language. Cross-entity
  data flow is a declarative typed binding (`target_field` → output); any real transformation/computation
  is **Policy**, applied by DCM — never in the spec (T2/T4).
- **Right altitude — model the contract, not the implementation or product surface.** A type/taxonomy
  captures the *concept and contract* (what a resource is, what it guarantees), never product/UI/impl
  detail (specific screens, feature lists, internal mechanics). Such detail belongs in specs/product
  docs and is referenced, not inlined. (Surfaced repeatedly in downstream review — e.g. enumerated UI
  surfaces, "document every field of this object," over-modeled internals.) Sibling of *minimal core*.
- **Simple common case; complexity is opt-in.** The common operation MUST be simple to declare — a
  consumer should not author elaborate structure for the ordinary path. Advanced/edge capability is
  *additive and optional*, never a tax on the default. (If "no admin would write this YAML," the altitude
  or the default is wrong.)
- **Cross-cutting mechanisms are consumer-neutral.** A shared mechanism (events, the four-state
  lifecycle, provenance, audit) serves *any* subscriber/consumer and is **never coupled to one engine or
  component** — e.g. lifecycle events route to all subscribers, not only the policy engine. (Pairs with
  whole-system reuse.)
- **Don't redefine a solved standard (active review gate, T5).** Before defining or redefining vocabulary
  or a concept — versioning, auth/identity, DR objectives (RTO/RPO), health probes, etc. — check for a
  credible external standard and **adopt it by reference or justify why not** (§22–23). Re-expressing a
  solved standard as bespoke vocabulary is a review finding, not a default.
- **Claims match the schema (reinforces §4).** A validation/typing *claim* MUST be backed by an actual
  typed schema — no open/untyped maps where the contract asserts "all fields validated." An untyped
  escape hatch that contradicts a stated guarantee is a defect.

## Candidate / deferred data points

Fields that were considered but are deliberately **not** in the meta-schema yet — recorded so the
rationale isn't lost or re-litigated. Default to **not** adding: a field earns inclusion only when there
is a clear need/value **and** it is not cleanly derivable from what already exists (minimal-core, §
Design principles; don't denormalize derivable facts).

| Candidate | Where it would live | Status | Why deferred · inclusion trigger |
|---|---|---|---|
| `ownership_model` (`whole-allocation` \| `allocation` \| `shareable`) | resource type spec | **Deferred** (2026-06-27) | Would be a policy anchor for decommission-safety / cost-attribution / placement (`foundations/ownership-sharing-allocation.md`). Deferred because: every current type is `whole-allocation` (no discrimination yet), the pattern is largely **derivable** from pool/stake relationships (denormalization → drift risk), and it may be **instance-level** for types realizable multiple ways (static vs pooled IP). **Add when** the first non-whole-allocation type is authored (a pool → `allocation`, or a declared-shareable resource), as the *authoritative declaration the relationships conform to* — not a derived copy. |
| `stability` (`experimental` \| `stable`) | resource type spec | **Deferred** (2026-06-27) | An explicit per-type maturity marker, separate from lifecycle `status` (`active`/`deprecated`/`retired`). Deferred because **maturity is already carried by the version** (`0.x` pre-stable → `1.0` stable, K8s-style — see VERSIONING.md "Lifecycle vs. maturity"), so a per-type field is redundant while the whole spec is `0.x`. **Add when** per-type maturity must differ from the global `0.x/1.0` (e.g. one type is battle-tested while the spec is still pre-1.0). The review stage (`developing`/`proposed`) is a governance-workflow concern, never a `status`/`stability` value. |

---
_E1–E5 reference the enhancement opportunities surfaced from dcm-project/enhancements#55
(constraint profiles, typed outputs, conditional constraints, layered-overlay provenance,
instance↔version pinning). This rubric will tighten as the standards survey + OSAC research land._

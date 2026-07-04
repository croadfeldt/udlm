# Research: minimizing custom surface & limiting dependency-graph breaks

**Type:** research note (decision support — not normative)
**Date:** 2026-07-04 · **Method:** multi-source deep-research harness; every claim
adversarially verified by 3 independent fact-checkers against primary sources (≥2/3
refutations kill a claim; 3 claims were killed and are excluded). 12 findings survived.
**Feeds:** #198 (extension model), #219/#220 (estate store), OBS/DEP rules, VERSIONING.md.

## Question

(a) How do mature interoperable models MINIMIZE bespoke data/methods — what are the real
adopt-vs-invent criteria? (b) What proven mechanisms LIMIT dependency-graph breaks
(referential integrity, dangling references, schema/edge evolution)?

## Verified findings (all vs primary sources)

**Identity & references**
1. **UUID-authoritative + advisory names is THE proven pattern** (K8s: every object carries
   a `uid`, typically RFC 4122, existing to distinguish a same-named deleted-and-recreated
   object; valid ownerReferences carry name AND uid, so a recreated owner is a *dangling
   edge*, never silently rebound). *UDLM's uuid+handle reference design is validated as-is.*
   Scope caveat: name-based late binding is legitimate for non-identity fields.
2. **Constrain the reference topology by design; machine-detect invalid edges** (K8s bans
   cross-namespace ownerReferences — "referential integrity problems that one party cannot
   solve" — and emits `OwnerRefInvalidNamespace` events; invalid refs resolve
   *deterministically*, never linger silently).
3. **Edges should be machine-maintained; integrity is a platform service** (controllers set
   ownerReferences; a dedicated GC controller enforces integrity — not consumers, not hand
   curation).

**Deletion & dangling references**
4. **Deletion is gated, not immediate — tombstone window is first-class** (deletionTimestamp
   + finalizers; object persists until cleanup conditions are met).
5. **Deletion-propagation is a per-request choice** (foreground / background / orphan), with
   ordering via blockOwnerDeletion + the DeletingDependents finalizer *in combination* (the
   over-broad "blockOwnerDeletion alone blocks deletion" formulation was REFUTED — it
   requires foreground propagation too).
6. **RFC 8345 defines degrade-don't-break**: a dangling leafref makes the instance
   *nonoperational* — removed from operational state but KEPT in intended state until the
   supporting object appears or the ref is repointed. Two projections, no data loss.

**Minimizing custom surface**
7. **Augment in a new module, never fork the base** (RFC 8345: technology-specific models
   are YANG augmentations of 4 base entities in NEW modules, `when`-conditioned).
8. **Uncoordinated extension is the documented failure mode** (≥92 modules augmenting
   RFC 8345 with inconsistent patterns — the inconsistency itself breaks multi-layer
   composability; the remedy chosen is a backward-compatible base revision, not bespoke
   workarounds). *Medium confidence — source is the expired draft-havel-nmop-digital-map;
   substance continues in active draft-ietf-nmop-simap-concept; monitor.*

**Evolution without breaking consumers**
9. **Redfish DSP0266 is the cleanest additive-only template**: minors add, never remove;
   deprecated elements are machine-annotated with the version-of-deprecation + favored
   replacement; removals only at majors.
10. **Redfish decouples edges from type versions**: references MUST target the *unversioned*
    definition (which carries no properties) — edges never break when a type revs.
11. **K8s compatibility rules are stricter than intuition**: even ADDING an enum value is
    backward-incompatible (unless the field is documented extensible); changes must
    round-trip across versions losslessly.

12. **Synthesis recommendation** (medium confidence, not externally verified as a unit) —
    see the action table below.

## Where UDLM/DCM already conforms

| Finding | UDLM/DCM today |
|---|---|
| 1 | uuid-authoritative + handle-advisory refs (identifier-scheme §2.3; estate CI enforces) ✅ |
| 3 (partially) | `connected_to` is LLDP-*discovered*, not hand-drawn; estate CI is the integrity service for git data ✅ |
| 9 | VERSIONING.md additive-minor / removal-at-major discipline ✅ |
| 10 | meta-schema `relationships.target` is the unversioned type NAME — edges already version-decoupled ✅ (codify as an explicit rule) |
| 7 | Tier-2 `Vendor.Type` namespace + `provider_hints` ≈ augmentation-in-new-module ✅ (make it the normative extension mechanism for #198) |

## Gaps → actions — APPLIED 2026-07-04

| # | Action | Landed at |
|---|---|---|
| 1 | Degrade-don't-break | `entities/service-dependencies.md` DEP-006 |
| 2 | Tombstone/two-phase delete | DEP-007 + estate validator retire-first gate (estate-repo) |
| 3 | Constrained reference topology | DEP-008 + estate validator TOPO-* checks (estate-repo) |
| 4 | Enum discipline + extensible markers | `registry/VERSIONING.md` (enum rows + §Enum extensibility); `device_class` marked `x-extensible-enum` (0.3.1) |
| 5 | `deprecated_in_version` | meta-schema `deprecation` object |
| 6 | Augment-only extension model | `registry/naming-conventions.md` §Extension model (seeds #198) |
| 7 | Reconciliation → DCM | division-of-responsibility note under DEP-006..008 |

### Original decision list (as proposed)

1. **Degrade-don't-break rule (adopt RFC 8345 §leafref semantics).** DCM runtime treats a
   dangling edge as *nonoperational + retained in intent*, never hard-fail, never silent.
   Estate CI stays hard-fail (authoring gate — validate-at-write). Add to OBS/DEP rules.
2. **Tombstone/two-phase delete.** Never hard-delete a referenced resource: `lifecycle_state:
   retired` first (uuid never reused — identifier-scheme §5 already forbids); estate CI to
   FAIL a removal that leaves inbound edges dangling and suggest retire-first.
3. **Constrained reference topology.** Declare which relationship kinds may cross which
   scopes (e.g. `contained_by` never crosses a sovereignty zone; `connected_to` only between
   physical interfaces). Validator emits machine-readable violations (K8s event analog).
4. **Enum discipline (adopt K8s rule).** Enum-value addition = breaking UNLESS the field is
   explicitly marked extensible. Add an `extensible: true` marker to the meta-schema for
   fields like `device_class` / `partition_mechanism`; note: the 0.2.0/0.3.0 device_class
   additions predate this rule — grandfathered, flagged honestly.
5. **Deprecation annotation carries version-of-deprecation** (Redfish): meta-schema
   `deprecation` has date/reason/replacement_uuid — add `deprecated_in_version`.
6. **Extension model for #198 = augment-only**: vendor/custom types augment Tier-1 bases in
   their own namespace; base edits require a base revision (never per-vendor forks) — the
   anti-pattern is finding 8's 92-module fragmentation.
7. **DCM owns reconciliation** (finding 3): finalizer-style gating, identity correlation
   (#228), and GC-like cleanup are DCM-runtime concerns — DEFER from the spec; the spec only
   defines the states/edges they act on.

## Coverage caveats (honest limits)

Findings concentrate on Kubernetes, Redfish DSP0266, and RFC 8345(+SIMAP). **No claims
survived (or were produced) for TOSCA, ServiceNow CSDM/CMDB reconciliation, Terraform state
orphans, ETSI NFV, OpenConfig, Backstage, or schema registries — absent, not negative.**
Three claims were refuted (Redfish Oem naming detail; two over-broad blockOwnerDeletion/
propagation renderings) — do not cite those formulations. Finding 12 is synthesis, not
verified fact. Sources are stable normative docs except the NMOP/SIMAP track (evolving).

## Primary sources

- kubernetes.io/docs — garbage-collection, owners-dependents, finalizers; K8s
  api-conventions.md + api_changes.md (sig-architecture)
- DMTF DSP0266 (Redfish Specification) — versioning, deprecation annotation, unversioned refs
- RFC 8345 (ietf-network-topology) — leafref degrade semantics, augmentation pattern
- draft-havel-nmop-digital-map / draft-ietf-nmop-simap-concept — augmentation-consistency analysis

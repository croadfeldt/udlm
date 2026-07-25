# use-cases/ — the UDLM model-validation corpus

**What this is:** use cases that validate the *data model itself* — that a capability the model
claims is actually expressible, checkable, and gap-detectable. They are the model-side twin of the
DAV analysis corpus (the dcm repo's `dav/use-cases/`, where these are registered as analysis sets);
the YAML shape is the shared use-case schema, so a file is valid in both corpora unchanged.

**Why in this repo:** the resource-type base standard (SPEC-DESIGN §36) requires every new type to
ship corpus use cases proving its capability axes. Those UCs live beside the model they validate;
the DAV instance ingests them from here (or from the mirrored dcm set) for gap analysis runs.

- `binding-surface/` — the typed-outputs (E2) gap class: outputs declared per type, bindings
  contract-checked, fleet coverage queryable, worked-example currency. Born from the 2026-07-24
  registry review finding the output surface systemically inadequate for binding (median: one thin
  boolean; ~14 of 46 types binder-consumable; 5 empty and silent about why).
- `type-standard/` — the rule-36 gate classes beyond outputs: reference discipline (PVD-001),
  adopts-registration parity, relationship-target integrity. Deterministic halves enforced by
  `tests/check_type_standard.py` (baseline ratchet); these UCs keep the classes gap-analyzable.
- `multi-cluster/` — the Platform.Hub capability axes: provision-via-hub, hub-to-hub portability,
  control-residency sovereignty (hub jurisdiction vs spoke), self-managed-hub rehydration (the
  ADR-043 demotion rule under its hardest test).
- `bare-metal/` — replayable host provisioning intent (Metal3 surface, fix-wave PR-1): provision
  from intent; host rehydration by replaying intent onto replacement hardware.
- `storage-redundancy/` — the generic RAID model (fix-wave PR-2): degraded-pool drift with
  graph-walkable blast radius; hardware RAID declared as Pool intent at bare-metal provision;
  composed-topology fault tolerance across authoring personas (recursive vdev trees); the
  backend-owned aggregation semantics and the one-capacity-source pool boundary.
- `process-migration/` — automation intent as a peer of resource intent: engine migration by
  canary + cutover, blue/green verification by typed-output diff, staged promotion (application
  deployment discipline applied to automation), structural lock-in queries, engine-upgrade
  regression. Stage flow: docs/flows/automation-migration-and-promotion.md.
- `must-reject/` — the negative family: success = the system REFUSES the intent, and the refusal
  is typed, actionable, non-leaking (ADR-041 information-firewall behavior holds on the error
  path), and auditable. Six rejection surfaces: cross-tenant reference, sovereignty egress,
  inline credential literal (vs Security.CredentialRef), undeclared-output binding at request
  time, provider capability mismatch, and write-through-masked-projection.
- `class-versioning/` — the scoped-Class evolution contract (mixed semantics): additive and
  breaking Base Class changes with atomic recompilation and enumerated blast radius,
  intra-registry pins refused (registry ref = the only internal pin), organizational
  uuid-precise pins honored with enumerated debt, blue/green typed-output-diff promotion of
  re-pins, and element scope narrowing classified breaking (portability is part of compat).
- `change-control/` — the temporal layer on class versioning: change-management policies that
  gate and orchestrate WHEN adoptions occur — continuous adoption, maintenance windows, full
  ceremony for breaking changes, freezes with queued debt, break-glass expedites (evidence
  gates never waived), policy-composed staged rollout across estates, and dependency-ordered
  propagation within one.

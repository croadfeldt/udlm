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
- `process-migration/` — automation intent as a peer of resource intent: engine migration by
  canary + cutover, blue/green verification by typed-output diff, staged promotion (application
  deployment discipline applied to automation), structural lock-in queries, engine-upgrade
  regression. Stage flow: docs/flows/automation-migration-and-promotion.md.

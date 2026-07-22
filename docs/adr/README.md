# UDLM Architecture Decision Records

Short, reviewable records of significant UDLM data-model decisions — the **why**. Each is a
`DecisionRecord` with architecture scope (the ADR specialization — `entities/knowledge-family.md`
§4.5); UDLM **adopts the ADR/MADR format by reference**, it does not coin its own. DCM keeps its
own ADRs in `architecture/adr/` (the control-plane side); UDLM ADRs here cross-reference them.

**Referenced DCM ADRs (external — resolve in the DCM repo `architecture/adr/`).** UDLM docs cite these
control-plane decisions by their `DCM ADR-0XX` name; they are not defined here:

| Ref | Topic (as cited in UDLM) |
|---|---|
| DCM ADR-012 | (control-plane; cited by UDLM docs) |
| DCM ADR-013 | Override model (control-plane side of policy override) |
| DCM ADR-014 | Layer/authority seam |
| DCM ADR-016 / 017 / 018 | Discovery/inventory control-plane decisions |
| DCM ADR-019 | Placement (the placement engine + algorithm) |
| DCM ADR-020 | Placement-adjacent control-plane decision |
| DCM ADR-022 | Trust model (DCM brokers trust, never custodies it) |
| DCM ADR-023 | Scale-of-integration / denaturalization tiers |

The local sequence below is UDLM's own — ADR-001…033 all have files here. The **DCM** ADR numbers
referenced above overlap these same integers, so a bare "ADR-014" is ambiguous between the local
ADR-014 and DCM ADR-014. Always qualify a control-plane reference as `DCM ADR-0XX` (it resolves in the
DCM repo `architecture/adr/`, not here); an unqualified `ADR-0XX` means the local file below.

**Required lens (every ADR / DecisionRecord).** Each decision MUST state its **Data · Policy · Provider**
aspects — the three foundational abstractions (DCM ADR-002). *Data* = what's modeled/held (UDLM);
*Policy* = what's decided/computed/governed (DCM); *Provider* = what's declared as possible and what
executes the mechanism. A decision that can't name all three (or explicitly say "n/a, because…") isn't
fully scoped. Foundational across UDLM, DCM, and DAV (`SPEC-DESIGN-REQUIREMENTS` §29).

| ADR | Decision | Status |
|-----|----------|--------|
| [001](ADR-001-topology-type.md) | `Topology` — cross-cutting failure/locality-domain type (failure domains = data within it; abstract `kind` / concrete `id`) | Proposed |
| [002](ADR-002-capacity-utilization-served-overlay.md) | Capacity/Utilization — served observational overlay (cost pattern), **not** a UDLM type | Proposed |
| [003](ADR-003-data-mobility-and-process-validation.md) | Data mobility (requirements=data, methods=provider, mechanism=provider, permission=Policy) + process-validation lifecycle (rehearsal/simulation, freshness; T6) | Proposed |
| [004](ADR-004-provider-capability-declaration.md) | Provider capability declaration — `topology_capability` + `mobility` + `operational_capability`; what placement & operational/SRE policies match against | Proposed |
| [005](ADR-005-time-integrity.md) | Time integrity — ordering is structural (hash-linked sequence + causal DAG, not clocks); time-sync is a profile-declared adopt-by-reference capability enforced by placement; cross-peer integrity via mutual signed checkpoints; leap-seconds require-monotonic/recommend-smear | Proposed |
| [006](ADR-006-convergence-control-model.md) | Convergence control model — Data·Policy·Provider are peers in an event-condition-action loop where **policy is re-entrant** (re-triggered by provider change/denial/drift); soundness rules = bounded convergence, idempotent re-entry, causal audit of triggers | Proposed |
| [007](ADR-007-profile-model.md) | Profile model — profiles are composed **sets** (policies + operational config + required mechanics), not levels; they set floors; built-in profiles are immutable and modification **forks a custom profile**; org-defined mechanics (e.g. approval ladder); platform-scoped now, group-scopable later | Proposed |
| [008](ADR-008-udlm-dcm-boundary.md) | The UDLM/DCM boundary — the peer test (could an independent peer do this differently and still be valid? yes→DCM, no→UDLM); UDLM = wire-compatible substrate, DCM = one realization; wire-compatibility not implementation portability (K8s precedent) | Proposed |
| [009](ADR-009-dependency-fulfillment.md) | Dependency fulfillment — who procures a dependent resource, and how a type accommodates a broker | Proposed |
| [010](ADR-010-dependency-graph-completion.md) | Dependency-graph completion — fault domains, blast radius, and the unmet-dependency diagnostic | Proposed |
| [011](ADR-011-validate-and-reserve.md) | Validate-and-reserve — two-phase realization | Proposed |
| [012](ADR-012-data-references.md) | Data references — the object-reference shape for shared reference data (uuid-authoritative, version-pinned) | Proposed |
| [013](ADR-013-hardware-component-scope.md) | UDLM/DCM is not a hardware component system-of-record (for now) — control plane, not DCIM | Accepted |
| [014](ADR-014-resource-type-optionality-conformity.md) | Resource-type data — optionality with conformity (transport, not policy) | Accepted |
| [015](ADR-015-settings-and-config-bundles.md) | Settings and configuration bundles | Proposed |
| [016](ADR-016-resource-type-role-graph-audit-not-config.md) | What a Resource Type models — the portable definition; provider-specific config stored extra; DCM is the state system-of-record | Proposed |
| [017](ADR-017-profile-homelab.md) | The Homelab profile — the single-operator on-ramp | Accepted |
| [018](ADR-018-profile-dev.md) | The Dev profile — the evaluation / co-engineering target | Accepted |
| [019](ADR-019-profile-standard.md) | The Standard profile — baseline production | Accepted |
| [020](ADR-020-profile-prod.md) | The Prod profile — hardened production | Accepted |
| [021](ADR-021-profile-fsi.md) | The FSI profile — regulated (financial-services) production | Accepted |
| [022](ADR-022-profile-sovereign.md) | The Sovereign profile — data sovereignty (strictest floor) | Accepted |
| [023](ADR-023-host-networking-as-data-nmstate.md) | Host networking as data — adopt NMstate + RFC 8344 for the addressing family | Accepted |
| [024](ADR-024-filling-provider-required-inputs.md) | Filling provider-required inputs — layers stage data, policies refine and validate | Proposed |
| [025](ADR-025-resource-references.md) | Resource references — AEP-124 resource association, resolved at reserve | Proposed |
| [026](ADR-026-typed-classification-naming.md) | Typed-classification naming — `<noun>_type` convention (`resource_type`/`entity_type`/`edge_type`); `type` namespaced by noun, not synonyms; `kind` retired for edges (non-standard + k8s object-`kind` collision), may remain for source discriminators | Accepted |
| [027](ADR-027-entity-family-model.md) | Entity family model — `family` = state vs execution (Resource/Process/Knowledge/Access); `entity_type` = Atomic/Composite shape from DCM's orchestration perspective; retire infrastructure/persistent/durable; `resource_type` = specific tier | Accepted |
| [028](ADR-028-rule-id-naming-and-registry.md) | Rule-ID naming + central registry — `PREFIX-NNN`, one prefix = one family = one home file, immutable IDs; `registry/rule-id-registry.yaml` is the source of truth; `check_single_source.py` (now CI-wired) enforces registered + single-homed | Accepted |
| [029](ADR-029-inventory-ancillary-types.md) | Inventory — optional ancillary observed-resource types (`classification: ancillary`, observe-only, `contained_by` substrate); opt-in via profile + capability + optional tier (no new mechanism); DCM stays the SoR for what it owns, not a complete inventory SoR; refines ADR-013; revives Hardware.Processor/StorageDevice/GraphicsProcessor | Proposed |
| [030](ADR-030-convergence-lifecycle-model.md) | The convergence lifecycle — one model beneath the families: Intent + Realized + a gap + Converge (ADR-006 completed); one act, two trigger-classes (intent-moved/target-moved); decommission is an intent value not an act; nature (maintained/work-product/curated) is durable, timeline/terminal/provenance are parameters; Resource/Process/Credential/Inventory/Knowledge are archetype presets. Post-1.0 direction; refines ADR-027 | Proposed |
| [031](ADR-031-one-zero-scope-focus.md) | 1.0 scope + focus — the 21 September use cases are the sole gravity well for 1.0 implementation; everything else is a minimal operational unblock or a Proposed ADR (binds nothing); remaining = ratify ADRs + conformance + 0.1→1.0 restamp | Accepted |
| [032](ADR-032-post-one-zero-direction.md) | Post-1.0 direction — "pre-1.0, pay only to remove a future-contradiction, never to pre-build a feature"; the one contradiction to avoid is hardening Resource/Process into closed species; cards on the table are Proposed ADRs; records the convergence-model direction for future-us | Proposed |
| [033](ADR-033-templates.md) | Templates — the orderable assembly, and Pattern → Template → System as the ADR-030 lifecycle (Intent → Requested → Realized) at assembly scale; Template ≈ TOSCA Service Template / OAM Application (chosen over the vendor-in-retreat "Blueprint"); Pattern = type-level intent in Knowledge (Antipattern's twin); processes bound not contained; Day-N a projection; composable infra is a Provider capability (ADR-004); on-ramp to LikeC4/C4/TOSCA. Post-1.0 direction | Proposed |
| [034](ADR-034-composite-service-is-template.md) | Composite Service **is** a Template (proposed / eng-discussion) — one orderable-composite tier, not two names for one objective; Template adopts catalog-item.schema.json as its 1.0 grounding (Composite Service = resources-only Template); Composite Entity → System; CMP-* → TPL-*; finishes retiring the "composite" tag after ADR-027 single/multi. Binds nothing until ratified | Proposed |

# Spike — can UDLM emit a TOSCA profile? (`Compute.VM`)

**Status:** research spike (non-normative). **What it settles:** the two questions the prior-art positioning
doc left falsifiable ([`../design/prior-art-and-positioning.md`](../design/prior-art-and-positioning.md) §9,
exit-1): (1) *does the UDLM type contract round-trip to a standard TOSCA node type?* — the implementability
proof — and (2) *should we "just extend TOSCA" instead of keeping the model?* Feeds the interop track (task
#54). **Method:** derive a candidate TOSCA v2.0 node type directly from the shipped
`Compute.VM@0.6.4` spec (properties, outputs, relationships), then record what mapped cleanly,
what was awkward, and what TOSCA has no native home for. This is a **paper mapping**, not a run through an
orchestrator — see *Limits*.

## Update — Q1 is now **mechanical**, across the whole registry

The paper mapping below has been made a tool:
[`registry/tools/tosca_emit.py`](../../registry/tools/tosca_emit.py) emits a TOSCA v2.0 node type from a
UDLM resource-type spec, recovers the UDLM-relevant facts back out of the emitted TOSCA, and diffs them
against the source. Result:

- **`Compute.VM@0.6.4`** — 9 properties, 9 attributes, 4 edge targets, and the version all
  round-trip with **0 loss, 0 invention**.
- **48 / 48 shipped type specs** round-trip **CLEAN** on the type + topology layer — the emitter is faithful
  across the *entire* registry, not one hand-picked type.

So Q1 (does the contract round-trip to a standard node type?) is answered **by tooling, not assertion**:
every UDLM type mechanically produces a lossless TOSCA node type. What the tool *cannot* carry is exactly the
delta (four-state lifecycle, sovereignty, attestation) — it rides as opaque `metadata`, which is the finding,
not a defect. Run: `python3 registry/tools/tosca_emit.py --round-trip <spec>`.

---

## The candidate node type (derived mechanically from the spec)

```yaml
tosca_definitions_version: tosca_2_0
node_types:
  udlm.compute.VM:
    version: 0.6.4                                  # ← UDLM entity version (MAJOR.MINOR.REVISION)
    derived_from: tosca.nodes.Compute
    metadata:
      udlm_id: "udlm/0.1/Compute.VM/0.6.4"   # ← the $id (identity + version pin)
      # DELTA — no native TOSCA home; carried as metadata (see below):
      udlm_sovereignty_zone: "<createOnly>"
      udlm_data_classification: "<createOnly>"
    properties:                                     # ← UDLM spec.properties (INTENT)
      guest_os:      { type: string, required: true }      # the one required field
      instance_size: { type: string, required: false, constraints: [ valid_values: [ small, medium, large ] ] }
      vcpu:          { type: map,    required: false }      # UDLM object → TOSCA map
      memory:        { type: map,    required: false }
      firmware:      { type: string, required: false }
    attributes:                                     # ← UDLM outputs (REALIZED — runtime-observed)
      primary_ip:      { type: string }
      ip_addresses:    { type: list, entry_schema: string }
      hostname:        { type: string }
      mac_addresses:   { type: list, entry_schema: string }
      provider_handle: { type: string }             # provider-native id ↔ the UDLM identity correlation
      instance_id:     { type: string }
      run_state:       { type: string }
    requirements:                                   # ← UDLM relationships (EDGES)
      - facility:   { node: udlm.facility.Location,       relationship: tosca.relationships.DependsOn, occurrences: [ 0, 1 ] }         # references Facility.Location 0..1
      - network:    { node: udlm.network.VirtualNetwork,  relationship: tosca.relationships.network.LinksTo, occurrences: [ 0, UNBOUNDED ] }  # references Network.VirtualNetwork 0..n
      - storage:    { node: udlm.storage.Volume,          relationship: tosca.relationships.AttachesTo, occurrences: [ 0, UNBOUNDED ] } # depends_on Storage.Volume 0..n
      - ip_address: { node: udlm.network.IPAddress,       relationship: tosca.relationships.DependsOn, occurrences: [ 0, UNBOUNDED ] } # depends_on Network.IPAddress 0..n
    interfaces:
      Standard:                                     # ≈ realize; DELTA: no native reserve-then-commit barrier
        type: tosca.interfaces.node.lifecycle.Standard
        operations: { create: {} }                  # ≈ the commit-phase build
```

The point: this was a **mechanical derivation** — every property, attribute, and requirement came straight
from the spec. A contract that can be transcribed to a standard node type without invention is, by that
measure, well-formed and implementable. **Q1 (does it round-trip?) → yes, for the type + topology layer.**

## Mapping — what landed where

| UDLM construct | TOSCA construct | Fit |
|---|---|---|
| resource type + `$id`/version | `node_type` + `version` + `metadata.udlm_id` | **clean** |
| `derived_from` (Base/Type/Provider, ADR-038) | `derived_from` (node-type inheritance) | **clean** — same shape |
| `spec.properties` (intent fields) | `properties` | **clean** |
| `outputs` (realized values) | `attributes` (runtime) | **clean** |
| `relationships[]` / `edge_type` | `requirements` + relationship types | **clean** — TOSCA relationship types are what ADR-026 already aligns to |
| `constraints`/enums | property `constraints` | **clean** |
| **four states** (Intent/Requested/Realized/Discovered, immutable records) | node_template (desired) + instance attributes (runtime) | **awkward** — TOSCA carries ~2 states (desired + runtime), not four immutable records; **Discovered / brownfield-first has no native model** |
| **validate-and-reserve** two-phase barrier (ADR-011) | `interfaces`/workflows | **awkward** — expressible only as a custom workflow; the reserve-then-commit *guarantee* isn't a native construct |
| **sovereignty / data_classification** (P4, createOnly) | — | **absent** — no native slot; lands in `metadata` or a bespoke `policy_type` |
| **attestation / provenance** (R2, field-level) | — | **absent** — no native construct |
| **policy-as-information-firewall** (ADR-041) | TOSCA `policies` (coarse) | **absent-ish** — TOSCA policies are declarative tags, not the ingress/egress firewall model |

## The delta — what TOSCA does not natively carry

The clean rows are the **type + topology** layer. Everything UDLM adds over "a typed topology" is exactly
the **awkward/absent** set: the **four-state immutable lifecycle** (intent-vs-realized as a portable dual
track + Discovered/brownfield), **sovereignty/provenance/attestation as first-class data**, and the
**reserve-then-commit guarantee**. That is the same delta the positioning doc named (§5) — the spike turns
it from an assertion into an observation: map a real type and the delta is precisely what falls out of TOSCA.

## Ergonomics

TOSCA v2.0 node types are a **good interchange target** — the type/property/attribute/requirement grammar is
close enough that emission is near-mechanical, and TOSCA is a real OASIS standard with orchestrator
implementations. The friction is entirely in the delta: expressing the four states + sovereignty +
attestation requires bespoke `metadata`/`policy_type` conventions that a generic TOSCA orchestrator won't
*understand* — it would carry them as opaque annotations, not enforce them.

## Verdict

**Q2 — should we "just extend TOSCA" instead?** No — but not "no" defensively. The honest outcome is
**publish a TOSCA interop profile for the type + topology layer, and keep the UDLM model for the delta:**
- TOSCA cleanly carries what it's designed for (typed nodes + relationships) → **emit/ingest a profile** (adopt-by-reference, task #54). This is a *strength to claim*, not a threat.
- TOSCA has **no native model** for the four-state lifecycle, sovereignty, provenance, or the reserve/commit
  guarantee → these stay UDLM's, expressed *through* TOSCA extensions where interop needs them.
- So "extend TOSCA" would mean re-inventing the four-state lifecycle + sovereignty *inside* TOSCA metadata —
  strictly more surface for strictly less enforcement. The delta is real and load-bearing; the model earns
  its existence (positioning doc §5), and TOSCA is an **emission target**, not a replacement.

**Q1 — implementability (the C-2 by-construction proof):** the mechanical derivation succeeded, so the
`Compute.VM` contract is well-formed enough to transcribe to a standard node type without
invention. Where TOSCA *couldn't* carry a thing, that thing was a deliberate UDLM addition, not a spec
defect. This is positive evidence for [`../implementing-a-resource-type.md`](../implementing-a-resource-type.md).

## Recommendation

1. **Adopt the finding, not a build:** record "TOSCA = interop-profile target for the type/topology layer;
   the lifecycle + sovereignty + attestation are the retained delta" as the interop-track (#54) starting
   position. A full generator is post-1.0.
2. **If eng wants the stronger proof:** the next increment is a *round-trip* — emit this node type from the
   spec by tool, ingest it back, and diff — which would move Q1 from "paper" to "by tooling." Small, and it
   would harden the implementability claim.

## Limits (honest scope)

Paper mapping of **one** type by hand — not run through an orchestrator, not round-tripped by tooling, not
covering composite/Process/Knowledge families. The clean rows are high-confidence (grammar is close); the
"awkward/absent" rows are the defensible core, but the *exact* extension shape (metadata vs `policy_type` vs
a TOSCA profile namespace) is unsettled and is itself part of task #54. No claim survives for TOSCA
**workflows** modelling the full convergence loop — untested here.

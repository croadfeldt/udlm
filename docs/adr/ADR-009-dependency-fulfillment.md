# UDLM ADR-009: Dependency fulfillment — who procures a dependent resource, and how a type accommodates a broker

**Status:** Proposed
**Date:** 2026-07-13
**Type:** Architecture Decision Record (a `DecisionRecord` with architecture scope — `entities/knowledge-family.md` §4.5)
**Related:** ADR-006 (convergence control model — DCM drives the single re-entrant loop); ADR-011 (validate-and-reserve — two-phase RESERVE→COMMIT is the decision-of-record for the realize-time criteria mechanism this ADR only names); ADR-008 (UDLM/DCM boundary — the peer test applied in §5); ADR-004 (provider capability declaration); `contracts/provider-contract.md` §6a (reserve/commit/release verbs); `registry/catalog-item.schema.json` (constituents carry `fulfillment`); `docs/graph-integrity.md` (cycle detection)
**Tracking:** The recurring "who defines and procures a catalog item's dependencies — the request or the provider" question. This ADR is the decision-of-record so it is not re-litigated.

## Context

A catalog item composes resources — a VM that needs storage, a network attachment, an IP. When it is realized, **who procures each dependent resource, and where does the information to specify it come from?** The debate recurs as a binary — *the request defines it* vs *the provider defines it* — but neither is complete: the information is **split across three parties at three times**, and none holds all of it.

- The **catalog item** (authored by the provider) declares that a *structural* dependency exists and which inputs the consumer must supply.
- The **consumer** knows the *intent parameters* — segment, location, sovereignty zone — but not the mechanics.
- The **realizing provider** knows the *realization-time specifics that do not exist until placement* — the segment a placement can actually reach, the host it landed on, driver constraints.

So the real question is not "who procures it" but **"who contributes which fields, when, and who drives the loop."** The last part has one answer under ADR-006, and it collapses the rest of the debate.

## Decision

### 1. DCM always orchestrates; it is the single policy and cycle-detection chokepoint

In every mode below, **DCM drives the convergence loop (ADR-006) and every dependency request flows through its policy pipeline** (placement, governance, sovereignty, quota) and cycle detection (`graph-integrity.md`). A provider never reaches around DCM to another provider. What varies across modes is only *who contributes the request's content, and when* — never who drives. This preserves the single convergent loop, uniform policy, central cycle detection, and cross-resource co-optimization.

### 2. Fulfillment is a per-dependency mode, declared in the catalog item

Each constituent declares a **`fulfillment`** mode, orthogonal to `provided_by` (which names the *realizer*: `self` = the registering provider, `external` = a DCM-placed provider). **`provided_by` = who realizes; `fulfillment` = who procures/contributes.**

| `fulfillment` | who contributes the request content | when | typical `provided_by` | use for |
|---|---|---|---|---|
| **`platform`** (default) | DCM's loop assembles it from catalog-declared `consumer_fields` | assembly-time | `external` | deps whose parameters are declarable up front — most IPs, storage |
| **`provider`** | the parent provider **computes the dependency's request criteria** from the request + realize-time facts and supplies them to DCM, which fulfills the *catalog-declared* dependency | realize-time | `self` | deps whose criteria the parent must compute, or that only exist post-placement |
| **`consumer`** | the consumer supplies an existing resource reference (BYO) | request-time | — | deps the consumer owns (BYO IP, DNS zone) |

`provider` mode is **not a separate provider request** and **not a passive output**. The dependency is *declared in the catalog* so DCM plans, places, governs, and cycle-checks it in advance; at realize-time the parent provider computes the specific criteria — which segment, which constraints — and hands them to DCM, which fulfills. DCM is always the fulfiller; `fulfillment` only says where the criteria originate — `consumer_fields` at assembly (`platform`) or the parent's computation at realize-time (`provider`). Declaring the dependency in the catalog is what lets **placement and policy act on it in advance** rather than discover it mid-realization; the catalog declaration *is* the request, made ahead of time (same mechanism as a Composite Service Definition, provider-contract §8.3).

### 3. A brokered dependency's target type MUST accommodate the broker's custom information

When a provider brokers a dependency it does not own, most of what it conveys is a **shared reference** both sides already understand (for a `Network.IPAddress`, the target `Network.VLAN` segment or `Facility.Location` — nothing bespoke). But some dependencies need **provider-specific realize-time state the base type does not model** (a vendor offload/QoS class, a driver constraint). For those, the target type **MUST be extensible in one of two sanctioned ways**, and the provider contract requires providers to consume whichever the target offers:

- **(a) Base-type extension surface** — the base type carries an open extension block (`spec` `additionalProperties` / a provider-extension layer, `domain: provider`, per `layering-and-versioning.md`); the base stays vendor-neutral, the extension is namespaced to the contributing provider.
- **(b) Custom resource type layered on the base** — a derived type (`entities/resource-type-hierarchy.md`) that `aliases`/extends the base and adds the broker's fields as first-class. Used when the shape recurs enough to deserve its own type.

Either satisfies the requirement (minimal-surface: prefer (a) for one-offs, (b) when the shape recurs). **A type that cannot be extended either way is non-conformant for brokered fulfillment.** The point is the **complete, contextual exchange** between broker and owner — the broker can convey everything the dependency needs, faithfully typed and namespaced, rather than being flattened into whatever fixed vocabulary the base type happened to anticipate. Settling the shape ahead of time and validating it at admission is a benefit, not the point.

### 4. Relationships on a type are guidance, not a gate

Because a broker may attach requirements a type author never anticipated, a type's `relationships[]` are **illustrative templates + placement hints**, not a closed allowlist. Only relationships that are *structurally required* (a `Storage.Dataset` cannot exist without a `Storage.Pool`) are enforced (`enforcement: structural`); everything else is `example`. The validator's REL-001 is advisory; REL-002 (required structural edges) stays. We cannot pre-validate what a provider will create, so the type spec is guidance, not a gate.

### 5. Boundary placement (ADR-008 test)

Applying ADR-008's peer test — *could a peer do this differently and still be a valid realization of the same data?*

- The **`fulfillment` field, the three modes' wire meaning, and the extension mechanism** are **UDLM** — a peer must interpret a `fulfillment: provider` constituent and a provider-extension identically, or interop breaks.
- **How DCM's loop implements brokering, placement, and cycle detection** is **DCM** — a peer may orchestrate differently.

## Options considered

- **The request defines the dependency.** Incomplete — the consumer knows intent parameters but not the realize-time specifics (reachable segment, driver constraints) that only exist after placement.
- **The provider defines the dependency.** Incomplete — the provider knows realization mechanics but not the consumer's intent, and if the dependency is undeclared, DCM cannot plan, place, or cycle-check it in advance. Rejected as the sole model; folded in as `fulfillment: provider`, where the provider computes *criteria* for a *catalog-declared* dependency.
- **A provider→provider path that bypasses DCM.** Rejected: it breaks the single convergent loop. Only DCM sees the whole graph, so only DCM can apply uniform policy, detect cycles, and co-optimize across resources. Every mode therefore routes through DCM (§1); modes differ only in who contributes content.

## Illustration — a VM that needs an IP

Catalog item `vm-service` (VM provider), showing all three modes on its constituents:

```yaml
constituents:
  - component_id: vm
    resource_type: Compute.VirtualMachine
    provided_by: self          # the VM provider realizes this
    fulfillment: provider
  - component_id: ipaddr
    resource_type: Network.IPAddress
    provided_by: external      # a DCM-placed IPAM provider realizes it
    fulfillment: provider      # VM provider computes the IP criteria at realize-time; DCM fulfills
    depends_on: [vm]
    bindings:                  # the target Network.VLAN segment (a shared reference) scopes allocation
      - { from_component: vm, from_output: target_segment, to_field: segment_ref }
  - component_id: disk
    resource_type: Storage.Volume
    provided_by: external
    fulfillment: platform      # DCM assembles it from consumer_fields.size
    depends_on: [vm]
```

The IP case needs **no accommodation mechanism (§3)** — the broker conveys only a shared `Network.VLAN` reference the fabric provider owns; no NIC/MAC/switch-port crosses the boundary (binding a returned IP to a vNIC is the VM provider's own post-allocation concern). The realize-time criteria flow (reserve VM → compute IP criteria → reserve IP → commit) is **two-phase realization; that mechanism is the decision-of-record in ADR-011**, not restated here.

## Chicken-and-egg → ADR-011

`fulfillment: provider` creates an apparent circularity: the IP criteria derive from the VM's realize-time facts, but the VM depends on the IP. This is **not a modeled cycle** (the `depends_on` edge is one-directional; the mutuality is in realization ordering). **ADR-011 (validate-and-reserve) owns the resolution in full** — a side-effect-free RESERVE phase computes each dependent's criteria from its parent's *reserved* facts, a commit barrier validates the whole graph, then COMMIT builds in dependency order; a genuine hard cycle surfaces as `RESERVE_QUERY_ALL_EXHAUSTED` / `DependencyCycle` and is denied. Do not re-derive that loop here.

## Data · Policy · Provider

- **Data** — UDLM models the `fulfillment` mode on each constituent, the `enforcement` marker on relationships, and the extension surface / derived type that carries brokered fields. This is the wire vocabulary a peer must read identically.
- **Policy** — DCM decides, at the single chokepoint (§1): placement, governance, sovereignty, quota, and cycle detection over every dependency regardless of mode. `provider` mode additionally requires delegated authority/attestation (trust model) — a per-dependency policy flag, not a default.
- **Provider** — the parent provider declares the catalog dependency and, in `provider` mode, computes and supplies the realize-time criteria (via ADR-011's reserve). A brokered target-type provider must consume whichever extension mechanism (a) or (b) the type offers.

## Consequences

- **The circular debate is closed:** intent relationships are author-declared, realized relationships are provider-reported, procurement is a declared per-dependency mode. All three are true at different times — not competing answers.
- **Schema companions:** `catalog-item.schema.json` gains `fulfillment` on constituents; `resource-type-spec.schema.json` gains the `enforcement` marker and states the extension-accommodation requirement; `provider-contract.md` gains §1b (intent vs realized) and the §3 extensibility obligation.
- **`provider` mode has a trust cost:** brokering a sub-intent on the consumer's behalf requires delegated authority/attestation. Flag it per-dependency; it is a deliberate choice, not a default.
- **Cycle safety:** brokered sub-intents are ordinary DCM requests, so `graph-integrity.md` covers them; the composite `depends_on` graph is acyclic-enforced (CMP-002).
- **Use cases** (brokered dependency, BYO dependency, extension-vs-custom-type) are captured in the DAV validation corpus so a realization is tested against them.

# UDLM ADR-009: Dependency fulfillment — who procures a dependent resource, and how a type accommodates a broker

**Status:** Proposed
**Date:** 2026-07-13
**Type:** Architecture Decision Record (a `DecisionRecord` with architecture scope — `entities/knowledge-family.md` §4.5)
**Related:** ADR-006 (convergence control model — DCM drives the loop); ADR-011 (validate-and-reserve — the two-phase realization that resolves the chicken-and-egg without side effects); ADR-008 (UDLM/DCM boundary + the compatibility rule); ADR-004 (provider capability declaration); `contracts/provider-contract.md` §6a (reserve/commit/release verbs); `registry/catalog-item.schema.json` (composite-service-model.md); `docs/graph-integrity.md` (cycle detection)
**Tracking:** The recurring question of who defines and procures a catalog item's dependencies — the request or the provider. This ADR is the decision-of-record so it is not re-litigated.

## Context

A catalog item composes multiple resources — a VM that needs storage, a network attachment, an IP address. When the request is realized, **who procures each dependent resource, and where does the information to specify it come from?** This recurs as a binary — *the request defines it* versus *the provider defines it* — but neither is complete. The information needed to procure a dependency is **split across three parties at three times**, and none of them holds all of it:

- the **catalog item** (defined by the provider) declares that the *structural* dependency exists and which inputs the consumer must supply;
- the **consumer** knows the *intent parameters* they care about — network segment, location, sovereignty zone — but not the mechanics;
- the **realizing provider** knows the *realization-time specifics that do not exist until placement* — the network segment the placement can actually reach, the host it landed on, driver constraints (the assigned NIC/MAC are the provider's own internal facts, not cross-provider criteria).

So the real question is not "who procures it" but **"who contributes which fields, when, and who drives the loop."** The last part has one answer under ADR-006, and it collapses most of the debate.

## Decision

### 1. DCM always orchestrates; it is the single policy and cycle-detection chokepoint

In every mode below, **DCM drives the convergence loop (ADR-006) and every dependency request flows through its policy pipeline** (placement, governance, sovereignty, quota) and its cycle detection (`graph-integrity.md`). A provider never reaches around DCM to another provider. What varies across modes is only *who contributes the request's content, and when* — never who drives. This preserves the single convergent loop, uniform policy, central cycle detection, and cross-resource co-optimization.

### 2. Fulfillment is a per-dependency mode, declared in the catalog item

Each constituent of a catalog item declares a **`fulfillment`** mode (alongside the existing `provided_by`, which names the *realizer*: `self` = the registering provider, `external` = a DCM-placed provider):

| `fulfillment` | who contributes the request content | when | typical `provided_by` | use for |
|---|---|---|---|---|
| **`platform`** (default) | DCM's loop assembles it from catalog-declared `consumer_fields` | assembly-time | `external` | well-understood deps whose parameters are declarable up front — most IPs, storage |
| **`provider`** | the parent provider **receives the initial request, calculates the dependency's request criteria** (from the request + realize-time facts) and supplies them to DCM, which fulfills the *catalog-declared* dependency | realize-time | `self` | deps whose criteria the parent provider must compute, or that only exist post-placement |
| **`consumer`** | the consumer supplies an existing resource reference (BYO) | request-time | — | deps the consumer owns (bring-your-own IP, DNS zone) |

The two axes are orthogonal and both belong on the constituent: **`provided_by` = who realizes; `fulfillment` = who procures/contributes.** `provider`-mode is **not a separate provider request**, but it is more than a passive output. The dependency is *declared in the catalog* (so DCM plans, places, governs, and cycle-checks it in advance); at request-time the **parent provider receives the initial request, calculates the specific criteria the dependency needs** — which segment, which port, what constraints, using its own logic and realize-time facts — and **supplies those criteria to DCM**. DCM then **fulfills** the declared dependency with them: it places, governs, cycle-checks, and realizes. So DCM is the fulfiller and the provider supplies the *computed criteria*; `fulfillment` says where those criteria come from — `consumer_fields` at assembly (`platform`) or the parent provider's calculation at realize-time (`provider`).

**Why declare the dependency in the catalog at all?** Because the declaration is what lets **placement and policy act on it *in advance*** — DCM plans, places, governs, sequences, and cycle-checks the dependency *before* realization, rather than discovering it mid-realization. The catalog declaration *is* the request, made ahead of time; the provider never issues a redundant one. It is the same mechanism as a Composite Service Definition (provider-contract §8.3).

### 3. A brokered dependency's target type MUST accommodate the broker's custom information

When a provider brokers a dependency it does not own, most of what it conveys is a **shared reference** both sides already understand — for a `Network.IPAddress`, the target `Network.VLAN` segment (or `Facility.Location`), nothing bespoke. But some dependencies need **provider-specific realize-time state the base type does not model** (a vendor-specific offload or QoS class, a driver constraint). For those, the target resource type **MUST be extensible in one of two sanctioned ways**, and the provider contract requires providers to consume whichever the target offers:

- **(a) Base-type extension surface** — the base type carries an open extension block (`spec` `additionalProperties` / a provider-extension layer, `domain: provider`, per `layering-and-versioning.md`) into which the broker's custom fields are written. The base type stays vendor-neutral; the extension is namespaced to the contributing provider.
- **(b) Custom resource type layered on the base** — a derived type (`entities/resource-type-hierarchy.md`) that `aliases`/extends the base and adds the broker's fields as first-class. Used when the extension is substantial or reused enough to deserve its own type.

Either satisfies the requirement; the choice is the implementor's (minimal-surface: prefer (a) for one-off custom fields, (b) when the shape recurs). **A type that cannot be extended either way is non-conformant for brokered fulfillment.**

**Why this is required.** The goal is to let two providers — the broker and the resource's owner — **exchange the full, contextual information a shared dependency actually needs**, rather than be limited to whatever fixed field vocabulary the base type happened to anticipate. Usually that information is a **shared reference** both sides already understand (a segment, a location) and nothing bespoke crosses the boundary. Where a broker genuinely knows something the base type does not model (a driver constraint, a vendor offload flag), it must be able to convey it **completely and in context** to the owner. A base-type extension (a) or a custom type (b) is the mechanism that carries that information faithfully — namespaced and typed — so nothing the broker needs to say is dropped or flattened into an approximation. Settling the shape ahead of time and validating it at admission is a *benefit* of doing it this way, not the point; the point is the **complete, contextual exchange** itself — providers can say everything they need to say to each other about the dependency.

### 4. Relationships on a type are guidance, not a gate (companion to this decision)

Because a broker may attach requirements a type author never anticipated, a type's `relationships[]` are **illustrative templates + placement hints**, not a closed allowlist. Only relationships that are *structurally required* by the resource (a `Storage.Dataset` cannot exist without a `Storage.Pool`) are enforced (`enforcement: structural`); everything else is `example`. The validator's REL-001 is advisory; REL-002 (required structural edges) stays. We cannot pre-validate what a provider will create, so the type spec is guidance, not a gate.

### 5. Boundary placement (ADR-008 test)

Applying ADR-008's test — *could a peer do this differently and still be a valid realization of the same data?*

- The **`fulfillment` field, the three modes' wire meaning, and the extension mechanism** are **UDLM** — a peer must interpret a `fulfillment: provider` constituent and a provider-extension the same way, or interop breaks.
- **How DCM's loop implements brokering, placement, and cycle detection** is **DCM** — a peer may orchestrate differently.

## Worked example (end to end): a VM that needs an IP

**Catalog item `vm-service`** (defined by the VM provider), `consumer_fields`: `network_segment`, `location`, `size`. `constituents`:

```yaml
constituents:
  - component_id: vm
    resource_type: Compute.VirtualMachine
    provided_by: self            # the VM provider registers this composite
    fulfillment: provider        # (the VM itself is what the provider realizes)
    failure_effect: fatal
  - component_id: ipaddr
    resource_type: Network.IPAddress
    provided_by: external        # a DCM-placed IP/IPAM provider realizes it
    fulfillment: provider        # the VM provider calculates the IP criteria at realize-time; DCM fulfills
    depends_on: [vm]             # ordered after the VM is placed (acyclic — CMP-002)
    bindings:                    # realize-time criteria flow VM -> IP request
      - from_component: vm
        from_output: target_segment # the Network.VLAN segment the VM's placement reaches
        to_field: segment_ref       # the target segment (a shared reference) scopes the IP allocation
    failure_effect: fatal
  - component_id: disk
    resource_type: Storage.Volume
    provided_by: external
    fulfillment: platform        # DCM assembles it from consumer_fields.size
    depends_on: [vm]
    failure_effect: fatal
```

**Flow (two-phase — reserve → barrier → commit, ADR-011):**

*Intent.* Consumer submits `catalog_ref: vm-service`, `network_segment: dmz`, `location: rack-3`, `size: 100Gi`. Intent carries no IP — none is allocated yet.

*Reserve phase — validate + hold, no side effects.* DCM assembles, policy-evaluates, and reserves across the graph, reconciling to a fixed point. Nothing is built in this phase.
1. **Reserve the VM.** The VM provider validates and **holds** a placement (with a granted TTL), returning its realize-time fact: the **target `Network.VLAN` segment** the placement can reach (or, at coarsest, its `Facility.Location`).
2. **Compute + reserve the IP** (`fulfillment: provider`). The `Network.IPAddress` dependency was **declared in the catalog** (so DCM planned, governed, and cycle-checked it in advance). Its criteria are just that **target segment**: the VM provider supplies it through the `binding`, and DCM **reserves** the IP provider, which holds an allocatable address on that segment. If that segment's pool is exhausted (or policy denies), DCM **re-reserves** the VM on a different placement and recomputes — the reserve reconciliation loop — until the holds are mutually consistent.
3. **Reserve the disk** (`platform`). DCM assembles it from `size` and reserves a storage provider — no VM-provider round-trip.

*Commit barrier.* DCM commits **nothing** until every hold (VM, IP, disk) is valid and mutually consistent **and** all policy (placement, governance-matrix, cycle, quota) is green against the **fully reserved** graph.

*Commit phase — execute the holds, in dependency order.*
4. DCM **commits** each held reservation: the storage / IP / VM providers build, write Realized State, and **report realized relationships back** — the IP's UUID correlated to the VM (provider-contract §1a.5, §1b). The VM now `realized-depends-on` the IP as a **`soft`** edge (portable: on rehydration the IP is *remapped*, not preserved).

*Release / expiry.* Any hold not committed — validation failure, cancellation, or **TTL expiry** (an implied release that emits `reservation.expired`; DCM's watchdog backstops a silent provider) — is released. Because the reserve phase built nothing, **no half-built resource is ever left behind.**

**This case needs no accommodation mechanism (Decision §3).** What the broker conveys is a **shared foundational reference** — the target `Network.VLAN` segment (or `Facility.Location`), a resource the network/fabric provider owns (`docs/foundational-resources.md`), not a provider-invented field. `Network.IPAddress` references the segment natively; the IP provider allocates from that segment's pool. There is **no NIC, no MAC, no switch-port ref, no extension block, and no custom type** involved — binding a returned IP to a vNIC is the VM provider's *own* post-allocation concern, never something the IP provider needs. IP allocation is therefore a plain shared-reference dependency, **deliberately not** an instance of broker-accommodation. The two sanctioned mechanisms — **(a)** a provider-extension block or **(b)** a derived type — exist only for the genuinely rare case where a broker must convey provider-specific realize-time state the base type does not model; a shared segment/location reference is not that case.

Both are conformant. This is the concrete instance of Decision §3.

## Chicken-and-egg: realize-time criteria and validate-and-reserve

Provider-mode fulfillment where a dependency's criteria derive from the parent's **realize-time** facts creates a chicken-and-egg: the `Network.IPAddress` criteria need the VM's assigned port (a realize-time fact), but the VM needs the IP. This is **not a hard dependency cycle** (`docs/graph-integrity.md`) — the modeled edge is one-directional (VM `depends_on` IP); the mutuality is in *realization ordering*, not in the graph. It resolves through **validate-and-reserve** (ADR-011) — the two-phase realization the substrate provides (`foundations/four-states.md` §2.3a) — with **no live partial realization**:

1. **Reserve the parent.** DCM reserves the VM: the provider validates and **holds** a placement, returning its realize-time facts — the reserved **port** — building nothing.
2. **Compute the child criteria.** The parent provider calculates the `Network.IPAddress` criteria — the **target `Network.VLAN` segment** the reserved placement can reach (or its `Facility.Location`) — and supplies them to DCM. Nothing about the VM's NIC, MAC, or host networking is conveyed; the IP provider needs only where to allocate.
3. **Reserve the child.** DCM reserves the IP on that segment — an address is held, still nothing built.
4. **Commit barrier.** Only once the whole reserved graph is held-and-valid and all policy is green does DCM **commit** — building the VM and IP together, in dependency order.

No half-built VM ever exists: the reserved facts flow parent→child *before* either is committed, and an abort is a **hold-drop**, not a teardown. The catalog `depends_on` graph stays acyclic (the "VM needs IP" completion is a commit-order fact, not a modeled edge), so `graph-integrity.md` cycle detection is unaffected. A **genuine** hard cycle — where no reserve order yields the facts the next reserve needs — surfaces as `RESERVE_QUERY_ALL_EXHAUSTED` / `DependencyCycle` and is **denied**, not looped. Reserve and commit both run inside DCM's re-entrant convergence loop (ADR-006), which is why DCM must own them (§1): only the orchestrator can reserve across the parent/child boundary and hold the commit barrier.

## Consequences

- **The circular debate is closed:** intent relationships are author-declared; realized relationships are provider-reported; procurement is a declared per-dependency mode. All three are true, at different times — not competing answers.
- **Schema changes (this ADR's companions):** `catalog-item.schema.json` gains `fulfillment` on constituents; `resource-type-spec.schema.json` gains the `enforcement` marker on relationships and states the extension-accommodation requirement; `provider-contract.md` gains §1b (intent vs realized) and the §3 extensibility obligation.
- **`provider` mode has a trust cost:** brokering a sub-intent on the consumer's behalf requires delegated authority/attestation (the trust model). Flag it per-dependency; it is a deliberate choice, not a default.
- **Cycle safety:** brokered sub-intents are ordinary DCM requests, so `graph-integrity.md` cycle detection covers them; the composite `depends_on` graph is already acyclic-enforced (CMP-002).
- **Use cases** for this pattern (brokered dependency, BYO dependency, extension-vs-custom-type) are captured in the DAV validation corpus so a realization is tested against them.

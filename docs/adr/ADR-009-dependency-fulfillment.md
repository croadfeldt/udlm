# UDLM ADR-009: Dependency fulfillment — who procures a dependent resource, and how a type accommodates a broker

**Status:** Proposed
**Date:** 2026-07-13
**Type:** Architecture Decision Record (a `DecisionRecord` with architecture scope — `entities/knowledge-family.md` §4.5)
**Related:** ADR-006 (convergence control model — DCM drives the loop); ADR-008 (UDLM/DCM boundary + the compatibility rule); ADR-004 (provider capability declaration); ADR-019 (placement); `contracts/provider-contract.md`; `registry/catalog-item.schema.json` (composite-service-model.md); `docs/graph-integrity.md` (cycle detection)
**Tracking:** The recurring question of who defines and procures a catalog item's dependencies — the request or the provider. This ADR is the decision-of-record so it is not re-litigated.

## Context

A catalog item composes multiple resources — a VM that needs storage, a network attachment, an IP address. When the request is realized, **who procures each dependent resource, and where does the information to specify it come from?** This recurs as a binary — *the request defines it* versus *the provider defines it* — but neither is complete. The information needed to procure a dependency is **split across three parties at three times**, and none of them holds all of it:

- the **catalog item** (defined by the provider) declares that the *structural* dependency exists and which inputs the consumer must supply;
- the **consumer** knows the *intent parameters* they care about — network segment, location, sovereignty zone — but not the mechanics;
- the **realizing provider** knows the *realization-time specifics that do not exist until placement* — the assigned NIC/MAC, the host network the hypervisor actually landed on, driver constraints.

So the real question is not "who procures it" but **"who contributes which fields, when, and who drives the loop."** The last part has one answer under ADR-006, and it collapses most of the debate.

## Decision

### 1. DCM always orchestrates; it is the single policy and cycle-detection chokepoint

In every mode below, **DCM drives the convergence loop (ADR-006) and every dependency request flows through its policy pipeline** (placement, governance, sovereignty, quota) and its cycle detection (`graph-integrity.md`). A provider never reaches around DCM to another provider. What varies across modes is only *who contributes the request's content, and when* — never who drives. This preserves the single convergent loop, uniform policy, central cycle detection, and cross-resource co-optimization.

### 2. Fulfillment is a per-dependency mode, declared in the catalog item

Each constituent of a catalog item declares a **`fulfillment`** mode (alongside the existing `provided_by`, which names the *realizer*: `self` = the registering provider, `external` = a DCM-placed provider):

| `fulfillment` | who contributes the request content | when | typical `provided_by` | use for |
|---|---|---|---|---|
| **`platform`** (default) | DCM's loop assembles it from catalog-declared `consumer_fields` | assembly-time | `external` | well-understood deps whose parameters are declarable up front — most IPs, storage |
| **`provider`** | the realizing provider **brokers a sub-intent through DCM**, contributing realization-time specifics via a constituent `binding` | realize-time | `self` | deps whose parameters only exist post-placement, or where the provider owns IPAM / has special requirements |
| **`consumer`** | the consumer supplies an existing resource reference (BYO) | request-time | — | deps the consumer owns (bring-your-own IP, DNS zone) |

The two axes are orthogonal and both belong on the constituent: **`provided_by` = who realizes; `fulfillment` = who procures/contributes.** `provider`-mode is not "provider procures independently" — it is the provider submitting a sub-intent that DCM places, governs, dedups, and cycle-checks like any other request. It is the same mechanism as a Composite Service Definition (provider-contract §8.3); `fulfillment` just makes the choice explicit and per-dependency.

### 3. A brokered dependency's target type MUST accommodate the broker's custom information

When a provider brokers a dependency it does not own (the VM provider needs an `Network.IPAddress` the *IP* provider owns), it must be able to convey requirements only it knows — the NIC to bind, the MAC, the host network. The target resource type therefore **MUST be extensible in one of two sanctioned ways**, and the provider contract requires providers to consume whichever the target offers:

- **(a) Base-type extension surface** — the base type carries an open extension block (`spec` `additionalProperties` / a provider-extension layer, `domain: provider`, per `layering-and-versioning.md`) into which the broker's custom fields are written. The base type stays vendor-neutral; the extension is namespaced to the contributing provider.
- **(b) Custom resource type layered on the base** — a derived type (`entities/resource-type-hierarchy.md`) that `aliases`/extends the base and adds the broker's fields as first-class. Used when the extension is substantial or reused enough to deserve its own type.

Either satisfies the requirement; the choice is the implementor's (minimal-surface: prefer (a) for one-off custom fields, (b) when the shape recurs). **A type that cannot be extended either way is non-conformant for brokered fulfillment.**

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
    fulfillment: provider        # the VM provider brokers the request at realize-time
    depends_on: [vm]             # ordered after the VM is placed (acyclic — CMP-002)
    bindings:                    # realize-time facts flow VM -> IP request
      - from_component: vm
        from_output: primary_nic   # the NIC the hypervisor actually assigned
        to_field: x-libvirt.bind_nic
    failure_effect: fatal
  - component_id: disk
    resource_type: Storage.Volume
    provided_by: external
    fulfillment: platform        # DCM assembles it from consumer_fields.size
    depends_on: [vm]
    failure_effect: fatal
```

**Flow:**
1. Consumer submits intent: `catalog_ref: vm-service`, `network_segment: dmz`, `location: rack-3`, `size: 100Gi`. (Intent carries no IP — none is allocated yet.)
2. DCM assembles + policy-evaluates + places the **VM** (ADR-019). The VM provider realizes it and reports `primary_nic` as a realized output.
3. The **IP** constituent is `fulfillment: provider`: the VM provider brokers a `Network.IPAddress` sub-intent **through DCM**, with `network_segment: dmz` (from consumer_fields) and the NIC fact carried by the `binding` into `x-libvirt.bind_nic`. DCM policy-evaluates + cycle-checks + places an IP provider.
4. The IP provider allocates the address and **reports the realized relationship back** — the IP's UUID, correlated to the VM (provider-contract §1a.5, §1b). The VM now `realized-depends-on` the IP as a **`soft`** edge (portable: on rehydration the IP is *remapped*, not preserved).
5. The **disk** constituent is `platform`: DCM's loop assembles it from `size` and places a storage provider — no VM-provider round-trip.

**The extensibility, both ways (Decision §3):** the broker's `x-libvirt.bind_nic` field reaches `Network.IPAddress` either
- **(a)** as a provider-extension on the base type — `Network.IPAddress` carries an open `x-libvirt.*` extension block the libvirt provider writes and reads; the base type stays neutral; **or**
- **(b)** as a custom type `Network.IPAddress.LibvirtBound` that extends `Network.IPAddress` with a first-class `bind_nic`, registered as a provider-extension type.

Both are conformant. This is the concrete instance of Decision §3.

## Consequences

- **The circular debate is closed:** intent relationships are author-declared; realized relationships are provider-reported; procurement is a declared per-dependency mode. All three are true, at different times — not competing answers.
- **Schema changes (this ADR's companions):** `catalog-item.schema.json` gains `fulfillment` on constituents; `resource-type-spec.schema.json` gains the `enforcement` marker on relationships and states the extension-accommodation requirement; `provider-contract.md` gains §1b (intent vs realized) and the §3 extensibility obligation.
- **`provider` mode has a trust cost:** brokering a sub-intent on the consumer's behalf requires delegated authority/attestation (the trust model). Flag it per-dependency; it is a deliberate choice, not a default.
- **Cycle safety:** brokered sub-intents are ordinary DCM requests, so `graph-integrity.md` cycle detection covers them; the composite `depends_on` graph is already acyclic-enforced (CMP-002).
- **Use cases** for this pattern (brokered dependency, BYO dependency, extension-vs-custom-type) are captured in the DAV validation corpus so a realization is tested against them.

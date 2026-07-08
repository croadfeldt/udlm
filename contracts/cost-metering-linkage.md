# UDLM — Cost / Metering Linkage (PROPOSED)

**Document Status:** 🟡 PROPOSED — a possible method; see [ADR-COST-002](../registry/instances/adr-cost-metering-linkage.json)
**Related:** [ADR-COST-001](../registry/instances/adr-cost-metering-placement.json) (placement) | [information-providers.md](information-providers.md) | [capability-discovery.md](capability-discovery.md) | [ownership-sharing-allocation.md](../foundations/ownership-sharing-allocation.md)

> **This document maps to: DATA + PROVIDER.** It defines the *hooks* UDLM carries so a realization
> can exchange cost with an external cost engine. It defines no rates and no calculation — those are
> the engine's ([ADR-COST-001](../registry/instances/adr-cost-metering-placement.json)).

---

## 1. The reciprocal contract

Cost is a **two-way** contract between a UDLM-conformant realization (e.g. DCM) and a cost engine — neither side owns both halves:

```
                 outbound: metering inputs
   realization ───────────────────────────────▶  cost engine (serve_data:cost)
   (DCM)         resource ref + priced_by +          applies its cost model
                 resolved meterable dimensions        (rates, capex/opex math)
        ▲                                                     │
        └───────────────────────────────────────────────────┘
                 inbound: cost.attributed {capex, opex}
```

- **Outbound (UDLM/DCM → engine):** for a resource, the realization hands the engine (a) the `priced_by` cost-model reference and (b) the resolved values of the resource's meterable dimensions. This is the "give the engine a method to look up resource data."
- **Inbound (engine → UDLM/DCM):** the engine returns cost (`cost.attributed`, capability-discovery), which the realization **consumes** — attributing it to the owning tenant, and OPTIONALLY feeding it into its own decisions (placement, budgets). 

**The engine computes; it never decides.** No placement, budget, or quota decision is delegated into the cost calculation. Those decisions stay in the realization as **policy** ([ADR-COST-001](../registry/instances/adr-cost-metering-placement.json)), using returned cost as an *input*. The cost engine is a pure function: `(resource dimensions + cost model) → cost`.

---

## 2. The three hooks UDLM carries

### 2.1 Meterable dimensions (the cost surface) — `spec.metering`

On a Resource Type Spec, a `metering.dimensions[]` list declares **what** about the resource is measurable and **where** each value is resolved from. Each dimension: `name`, `unit`, `cost_class` (**capex** = capital/allocation, amortized; **opex** = operational/usage), and a `source`:

| `source.kind` | Meaning | Resolved by the realization from |
|---------------|---------|----------------------------------|
| `field` | a declared field/output | direct read of the Realized-state field named by `source.ref` |
| `lifecycle` | a time interval | the four-state clock (e.g. `realized_to_decommissioned`) — the amortization / usage window |
| `telemetry` | an external metric | a `serve_data` telemetry Information Provider, keyed by `source.metric` |

There is **deliberately no `formula`/`derived` kind** — UDLM declares *sources*, never computes. Combining dimensions into a number is the engine's job. This is the line that keeps calculation out of the data model.

### 2.2 Cost-model reference (the pricing anchor) — `priced_by`

A `priced_by` reference associates a resource with the external cost model that prices it:

```yaml
priced_by:
  information_provider_uuid: <the serve_data:cost provider — the cost engine>
  external_model_id: "onprem-baremetal-2026-q3"   # opaque to UDLM
```

- On a **Resource Type Spec** → the default for all instances of the type.
- On a **realized entity** → a per-instance **override** (per-customer / per-contract pricing, whose lifecycle stays external).

`external_model_id` is a black box: UDLM never defines the cost model's contents. **Which** `priced_by` applies (type default vs instance override, per customer/contract) is admin **policy**, not data.

### 2.3 The lookup contract (resolution)

Given an `entity_uuid`, a conformant realization MUST be able to resolve every declared meterable dimension to a value using its `source` (field read / lifecycle interval / telemetry lookup). That resolved set + `priced_by` is exactly the outbound half of §1. UDLM declares WHAT is meterable and WHERE each value comes from; the realization performs the resolution; the engine does the math.

---

## 3. Worked example — a bare-metal host, capex + opex

`Compute.BareMetalHost` v0.2.0 carries (see `registry/resource-types/compute.bare-metal-host.json`):

| Dimension | class | source | Meaning |
|-----------|-------|--------|---------|
| `installed_cores` | capex | field `spec.cpu.cores` | the hardware you bought … |
| `installed_memory` | capex | field `spec.memory.size` | … amortized over |
| `installed_storage` | capex | field `spec.storage.capacity` | … |
| `provisioned_hours` | capex | lifecycle `realized_to_decommissioned` | its in-service window |
| `power_kwh` | opex | telemetry `host.power.draw` | actual energy consumed |

`priced_by → onprem-baremetal-2026-q3` in the cost engine. DCM resolves the capex dimensions from fields + the lifecycle clock and the opex dimension from a power-telemetry provider, hands them to the engine with the `priced_by` ref, and consumes the returned `cost.attributed {capex, opex}`, attributing it to the host's owning tenant. A **VM** (`Compute.VirtualMachine`) follows the identical pattern — capex = allocated vCPU/memory/disk over `provisioned_hours`; opex = `cpu_hours_used`, `network_egress_gb`, `power_kwh`.

---

## 4. DCM side — enabling the hooks

The cost engine registers as a provider declaring the reciprocal need:

```yaml
provider:
  name: "cost engine"
  capabilities: { serve_data: { data_domains: [cost] } }
  needs_from_realization:
    - domain: entity_lifecycle    # realized/decommissioned → amortization windows
    - domain: metering            # the meterable dimensions
```

DCM's metering resolver walks each Resource Type's `metering.dimensions`, resolves values per `source`, and calls the engine with `{resource ref, priced_by, values}`. It consumes `cost.attributed`, attributes to the owning tenant (the accountability edge in [ownership-sharing-allocation.md](../foundations/ownership-sharing-allocation.md) §7), and MAY use the result as a placement/budget input — but that decision stays in DCM policy, never in the engine.

---

## 5. Data · Policy · Provider

- **Data:** `spec.metering` (the meterable surface) + `priced_by` (the cost-model reference). No rates, no formulas.
- **Policy:** which `priced_by` wins (type default vs per-customer instance override); whether returned cost gates placement/budget/quota — all admin policy in the realization.
- **Provider:** the cost engine (`serve_data:cost`) computes; a telemetry provider (`serve_data`) supplies opex usage. The realization consumes; neither decides on the engine's behalf.

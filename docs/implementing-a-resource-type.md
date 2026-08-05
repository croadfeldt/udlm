# Implementing a resource type — a worked walkthrough (`Compute.VirtualMachine`)

**Audience:** an engineer building **provider** support for a UDLM resource type.
**What this answers:** *"can we actually implement this?"* — yes, and here is the whole path for one type,
each step pointing to the obligation that governs it (this is a map, not a re-spec — it never restates the
contracts). It uses `Compute.VirtualMachine` throughout and **extends the four-states worked example**
([`four-states.md`](../foundations/four-states.md) §2.6) from *what each state record holds* to *what you do
to produce it*.

## The boundary — read this first, so you build the right thing

You implement the **provider side**: naturalize intent → reserve → build → denaturalize → report. You do
**not** decide policy, resolve placement, enforce sovereignty, or author the Realized graph — **DCM does**
([ADR-008](adr/ADR-008-udlm-dcm-boundary.md)). You **present evidence**; DCM **decides and records**. Most
over-building comes from crossing this line — see `sovereignty` / `policy` in [`GLOSSARY.md`](../GLOSSARY.md).

## The path, end to end

**0 · Declare what you support** — [`CONFORMANCE.md`](../CONFORMANCE.md) §4. Pick a conformance level +
profile; declare the surfaces you implement and the types + versions you support
(`Compute.VirtualMachine@<version>`). Register per [`provider-contract.md`](../contracts/provider-contract.md) §2.

**1 · Read the type spec** — [`registry/resource-types/compute/Compute_VM.json (generated — authored in registry/classes/compute.vm.yaml)`](../registry/generated/Compute_VM.json).
Its fields, typed `outputs`, edges, and `$id`/version are the **exact contract you validate against** — resolvable
offline, no runtime late-binding (VERSIONING publish law; P4 offline closure).

**2 · Naturalize the intent** — provider-contract §2, [`data-roles.md`](../contracts/data-roles.md). Translate
the UDLM request into your native VM representation. Only **execution-role** data is naturalized — role-filtered
by contract, not your discretion.

**3 · Validate-and-reserve — build nothing yet** — four-states §2.3a; provider-contract §6a;
[ADR-011](adr/ADR-011-validate-and-reserve.md). Validate against capacity/identity/policy, **hold** the result,
and return a **`reservation_hold_uuid` + your computed realize-time facts** (the address/port you *would* assign).
Write **no** Realized state. Release the hold on TTL or failure — because you built nothing, there is nothing to
compensate.

**4 · Commit at the barrier** — four-states §2.3a. Only when DCM signals the whole graph is reserved and policy is
green do you **build** the VM. This is the *only* phase that mutates infrastructure.

**5 · Denaturalize + report (the load-bearing step)** — provider-contract §1a.5, §1b. Translate the built VM back
to UDLM and report realized/discovered state **per resource** with the **identity correlation** (UDLM `uuid` ↔ your
native `vm_id`). **DCM writes Realized and authors the Realized relationships from your correlation** — you supply
the correlation, DCM sets the edge (§1b.2). Skip this read-back and DCM is blind to reality (§1a.5).

**6 · Observe continuously** — P2 (observability); four-states §2.4. Emit **Discovered** with `correlation_ids`
each cycle; DCM compares it against Realized to detect drift. You never write Realized from a discovery — discovery
only reports.

**7 · Stay in bounds** — provider-contract §2a (`SOV-*`), §4 (Governance Matrix), §5 (Zero Trust). Carry
`data_classification` and `tenant_uuid`; every edit or boundary crossing is governed exactly as any other, and a
provider-owned editor is **not** an audit bypass (§1a). You **enforce nothing** — you present classification +
evidence; DCM's Matrix decides.

## What you do **not** implement (the boundary, restated — it's where people over-build)

- **Policy, placement, sovereignty enforcement, the Realized graph** — all DCM (ADR-008). You supply facts and
  correlations; DCM decides and authors.
- **A central runtime the model depends on** — validation/conversion/cascade are *evaluable data* any host runs
  offline (G1); you are not required to stand up a controller for the model to be valid.

## "Could you build from this?" — the implementability self-test

Run this checklist against the cited contracts. Every box should be checkable **from the spec alone**:

- [ ] Read `Compute_VM.json (generated — authored in registry/classes/compute.vm.yaml)` **offline** and know every field's shape and every typed output.
- [ ] Naturalize using **only execution-role** data (data-roles).
- [ ] Reserve returning a **hold + computed facts** without building anything (four-states §2.3a).
- [ ] Commit **only** on the barrier signal.
- [ ] Denaturalize with an **identity correlation per resource** (provider-contract §1a.5).
- [ ] Emit **Discovered with `correlation_ids`** each cycle.
- [ ] Carry `data_classification` / `tenant_uuid` on every crossing (§2a).

If any box is **not** checkable from the cited contract, that is a concrete implementability gap — **file it**.
Surfacing exactly those is the point of this walkthrough.

## The deeper proof (scheduled next)

The strongest implementability evidence is emitting a working **TOSCA profile** for this type
([prior-art & positioning](design/prior-art-and-positioning.md) §9, exit-1): if the contract round-trips to a
standard profile with acceptable ergonomics, it is buildable **by construction** — and that same spike answers the
"why not extend TOSCA" question. Targeted before the 1.0 freeze.

## The contracts you build against (CONFORMANCE §5)

Required, not excludable — **foundations** (four-states, layering-and-versioning, data-model-core), **wire**
(identifier-scheme, error-model, event-catalog, schema-sharing), **operational** (provider-contract,
policy-contract, data-store-contracts). The **test suite** (CONFORMANCE §8) is what certifies you did it.

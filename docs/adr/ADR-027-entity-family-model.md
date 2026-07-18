# ADR-027: Entity family model — Resource | Process, and the Atomic/Composite shape

**Status:** Accepted (2026-07-17)
**Related:** [ADR-026 — typed-classification naming](ADR-026-typed-classification-naming.md); `foundations/entity-types.md`; `foundations/entity-type-families.md`; ADR-013 (hardware component scope)

## Context

The entity taxonomy previously named its primary Resource-family types `Infrastructure Resource | Composite | Process`, with `Infrastructure Resource` defined as a resource that "persists across time." Review exposed several problems:
- **`Infrastructure`** carried no model meaning — the model never branches on "infrastructure vs something else"; Infrastructure Resource and Composite were managed identically.
- **Persistence/duration is not the discriminator** — a one-hour VM and a multi-year cluster are the same kind; "persistent"/"durable" imply a longevity the model never tests, and "persistent" collides with container-storage usage.
- **`Composite` as a peer type** overstated it — a composite is managed exactly like any other resource, it merely owns constituents.
- **`Process` sat inside the Resource family** although a process is not a maintained state at all.

## Decision

**The primary entity axis is state vs execution, expressed at the `family` level; the coarse shape (owns constituents or not) is `entity_type`.**

### Families
`family ∈ { Resource, Process, Knowledge, Access }`:
- **Resource** — a **maintained state**: the system holds its desired/realized state and continuously reconciles reality to it (drift detection, suspend/resume, explicit decommission). *Duration is irrelevant.*
- **Process** — a **bounded execution**: runs to a terminal outcome (`COMPLETED` / `FAILED` / `CANCELLED`), never reconciled — no drift, no suspend. Automation is the archetype.
- **Knowledge** — curated information (Capability, TaxonomyTerm, …), anchored by DAV.
- **Access** — identity (`Identity`).

`Infrastructure` / `persistent` / `durable` are retired: an entity is simply a **Resource** (a maintained state).

### Shape — `entity_type ∈ { Atomic, Composite }` for Resource and Process
`entity_type` records the coarse shape: **Atomic** (owns no constituents) or **Composite** (owns constituents). Composite is *not* a separate kind or family — it is a shape either a Resource or a Process can take, carrying the same lifecycle, drift, ownership, and decommission machinery, plus a `composite_health` axis and declared constituents.

**The Atomic/Composite line is drawn from the realization's (DCM's) perspective — its orchestration scope — not the entity's internal complexity:**
- **Atomic** = a single thing DCM manages / a single call DCM makes. A VM is Atomic; an Ansible/AWX workflow *invoked as one call* is Atomic (the provider orchestrates its internal jobs, opaque to DCM).
- **Composite** = DCM owns/orchestrates more than one constituent — several managed resources, or several process calls DCM itself sequences.

A composite Resource's constituents are its owned resources; a composite Process's constituents are the sub-process calls DCM sequences — recorded via the **same constituent-relationship model** in both cases.

### Tiers
`family` (Resource | Process | Knowledge | Access) + `entity_type` (the coarse shape — never redundant with family) + `resource_type` (the specific type: `Compute.VirtualMachine`, `Automation.AnsiblePlaybook`). Vendor-specifics ("playbook") live in `resource_type`; the coarse, generic, policy-gateable distinction (`Atomic`/`Composite`) lives in `entity_type`. Both tiers are queryable and gateable.

## Consequences

- Every qualifier that carried no model meaning (infrastructure/persistent/durable) is gone; the axis is state vs execution.
- `entity_type` is meaningful in every family — no `family == entity_type` redundancy — and needs no separate `flavor` field.
- Composite is `entity_type: Composite`, queryable at the catalog **and** instance layers (structure alone can't classify a catalog item — `constituents[]` is realized-only).
- A registry migration: `family` enum +`Process`; `family: Resource` and `family: Process` → `entity_type ∈ {Atomic, Composite}`; existing specs `Infrastructure Resource → Atomic`, `automation.job → family: Process`.
- **Follow-up:** classify which existing specs are genuinely `Composite` (a real OpenShift VM owns its disks/pod) and model their `constituents[]`.
- Opens a clean correlation between AAP/AWX workflows and DCM-naturalized composite-process orchestration (constituents = job templates).

## Alternatives considered

- **Keep `entity_type: {Resource, Composite}`** (atomic = "Resource") — rejected: leaves `family: Resource / entity_type: Resource` redundant.
- **A separate `flavor` field** for atomic/composite — rejected: a third classification tier when `entity_type` already carries the shape; `flavor` couldn't be queried at the catalog layer without duplicating the signal.
- **Naming the persistent kind `Durable` / `Managed`** — rejected: `durable` implies longevity (not the discriminator); `managed` reserves a word better kept for a future managed-vs-unmanaged (observed/brownfield) axis.

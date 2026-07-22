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

## Addendum (Proposed, 2026-07-20) — derive the shape; don't store it as source of truth

**Status:** **Accepted & implemented** (2026-07-22) — the shape and `lifecycle_archetype` are now **derived**, not
stored. Meta-schema: `entity_type` dropped from `required` and required only on the Knowledge/Access branches;
`lifecycle_archetype` optional/derived. Registry: both fields removed from the 34 Resource + 1 Process specs
(`entity_type`) and from every spec that carried `lifecycle_archetype`, each MINOR-bumped (pre-1.0 incubation).
The in-flight `Atomic|Composite → single|multi` **rename is superseded** — a field being derived is not renamed.

**The question.** The shape asserts *"owns constituents?"* Does storing that flag add value beyond
filtering, or does the **constituent list already carry it**?

**Evidence (registry + spec scan, 2026-07-20).**
- **Distribution:** of the Resource/Process types, **33 are `Atomic`, 2 are `Composite`** (`storage.pool`,
  `storage.cluster`). *(The other `entity_type` values — `Capability` / `TaxonomyTerm` / `Identity` — are the
  Knowledge/Access **discriminators**, genuinely needed and out of scope here; this addendum concerns only the
  Resource/Process shape.)*
- **Behavioral consumers: none.** No policy, contract, validator, or lifecycle rule branches on
  `single`-vs-`multi`. It is used only for filtering / classification.
- **Derivability:** `multi ≡ has constituents`. For Templates / Composite Services (which **declare**
  constituents at catalog time) and for any realized entity (`constituents[]`), the shape is derivable.
  `storage.pool` declares its constituents; `storage.cluster` does not — the lone realized-only case, and
  nothing consumes its shape at catalog time.
- **Dependencies are NOT the signal.** `depends_on` is *"needs,"* the shape is *"owns."* An `Atomic` resource
  has dependencies; deriving the shape from dependency count would mislabel nearly every atomic resource.

**Proposal.** Treat the Resource/Process shape as a **derived predicate (`has_constituents`)** — computed
from the constituent list (declared for composites/Templates; realized for instances) — **not** a stored,
required source-of-truth field. This removes a duplicated data point (**T7**) and keeps derivation as
Policy/query (**T2**). The Knowledge/Access `entity_type` values are unaffected.

**The one thing that would reverse this:** a concrete use case that must **gate or query catalog-time
multi-ness for a type whose constituents are realized-only**. None exists today. If one appears, it carries
the justification for storing the flag — the flag should not be stored "just in case."

**Implications (now realized).**
- The `single`/`multi` rename branch (`feat/entity-type-single-multi`) is **superseded** — retired in favour of
  deriving `has_constituents`; the stored shape value is gone, so there is nothing to rename.
- Meta-schema: `entity_type` removed from top-level `required`; required only on the Knowledge/Access `allOf`
  branches (`Capability`/`Identity`/… **stay** — genuine discriminators). `lifecycle_archetype` optional/derived.
- `has_constituents` is the derived predicate: `true` iff the type/instance declares/holds `constituents[]`
  (Templates/Composite Services declare them at catalog time; realized entities carry them). No stored field.

### Second finding — `lifecycle_archetype`: same disposition

`lifecycle_archetype` (`provisioning` / `curation`) is the identical pattern and is bundled here:
- Its **own schema description** says *"inferred from `family` if absent."*
- Set explicitly on **22 types**, but **0 behavioral consumers** — nothing branches on it.
- Fully **derivable** (from `family` → `nature`).

**Proposal:** derive it, don't store it. It is already optional; make it a derived predicate and drop it from
authored specs. Zero migration risk (no consumer). Same reasoning, same disposition as the shape above — a
stored classifier with no consumer that its own description marks as inferable earns nothing beyond filtering.

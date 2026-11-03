# Estate observation — observe → normalize → quarantine-or-graph (the flow)

**What this settles:** how **observed** (inventory) resources enter the model: hardware components,
facility locations, directory identities, network fabric, derived topology. These are the resources a
provider *discovers* in the real estate rather than ones a consumer *requests*. A **lighter** flow: it
**builds on [uc-07-udlm-dependency-graph-data-model](uc-07-udlm-dependency-graph-data-model.md)** (the
graph the observations land in) and the provider contract (a provider populates the realized plane). It
documents only what observation adds: normalization to the model vocabulary, the **quarantine** gate on
off-vocabulary values, and the **refusal → audit record** cross-cut.

> **Use Cases:** `observed/estate-resource-observed` (positive),
> `observed/observation-off-vocabulary-quarantined`, `audit/refusal-emits-audit-record` (must-reject).
> **Personas:** platform-operator / information-provider-owner · **Perspective:** compliance-auditor.
> **Types this covers:** the hardware Bases (`GPU`, `BMC`, `Processor`, `StorageDevice`,
> `NetworkInterface`), the facility Bases (`Location`, `Topology`), `Identity`, `NetworkSwitch` and
> `VLAN`: every type populated *from* the estate rather than authored as intent.

**In one breath.** A provider observes a resource that already exists (a GPU, a BMC, a rack location, a
directory group) and ingests it as a **discovered** record. UDLM normalizes it to the model's published
vocabulary. A value the vocabulary doesn't define is **quarantined**, not silently blessed. A conforming
record is linked into the dependency graph with its observation provenance. Every rejection along the way
emits an audit record; auditability is stated once here, not re-derived per type.

## The flow

```mermaid
flowchart TD
    A["Provider observes a real resource<br/>Hardware / Facility / Identity / fabric"] --> B["Ingest as a discovered record<br/>+ observation provenance"]
    B --> C{"Values in the published<br/>model vocabulary?"}
    C -->|off-vocabulary field/value| Q["Quarantine — name the field + value;<br/>hold for reconciliation, never admit as valid"]
    Q --> AUD["Emit audit record<br/>(refusal ⇒ audit, single-source)"]
    C -->|conforms| D["Normalize to model vocabulary"]
    D --> E["Link into the dependency graph<br/>realized edges + provenance"]
    E --> F["Observed record queryable<br/>(blast-radius, SBOM/CVE, topology)"]
```

## What observation adds

- **Discovery, not request** — the resource exists; the provider reports it. The record is a discovered
  record with observation provenance (which provider, when), never an intent to fulfill.
- **Quarantine, not silent-accept** — an observed value outside the published vocabulary is held and
  surfaced (the field and value named), not admitted as if valid. The corpus publishes the vocabulary;
  observation conforms to it or is quarantined for reconciliation.
- **Auditability stated once** — every refusal (a quarantine included) emits an immutable audit record
  (AUD-006, the Merkle model). This is defined in `audit/refusal-emits-audit-record` and *referenced* by
  every refusal path, not restated. That is the single-source fix for a requirement that otherwise leaks
  into every scenario's analysis.

## What UDLM does not decide

How a provider discovers the resource (scan, agent, API), or its native inventory format (the
naturalization boundary, DCM ADR-023); the reconciliation workflow for a quarantined record (policy, the
control plane's). UDLM defines the observed record shapes, the published vocabulary they normalize to, the
quarantine contract, and the graph they link into.

## Where each piece is specified

| Piece | Contract |
|---|---|
| The dependency graph observations land in | `uc-07-udlm-dependency-graph-data-model.md`; UDLM estate model |
| Published vocabulary + quarantine-on-off-vocabulary | `use-cases/DIMENSION-VOCABULARY.yaml` (the DIM-001 gate, `tests/check_uc_dimensions.py`) |
| Refusal ⇒ audit record (single-source) | `audit/refusal-emits-audit-record`; AUD-006 |
| The observed record shapes + examples | `registry/generated/gpu.json`, `bmc.json`, `processor.json`, `storage-device.json`, `network-interface.json`, `location.json`, `topology.json`, `identity.json`, `network-switch.json`, `vlan.json` (`spec_examples`; register row 055) |
| Corpus | `use-cases/observed/`, `use-cases/audit/` |

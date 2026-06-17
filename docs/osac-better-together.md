# UDLM/DCM ↔ OSAC — Better Together

_Status: proposal / vision. Grounded entirely in public OSAC artifacts (`github.com/osac-project`,
research.redhat.com) and UDLM's own model. There is no announced partnership; this documents why the
two fit and how they would compose._

## The one-line story

**OSAC provisions platforms. UDLM is the universal data substrate that describes them. DCM operationalizes
that data.** OSAC is the *runtime that makes real*; UDLM/DCM is the *portable, governed, auditable data
lifecycle around it*. Each is strong alone; together they cover the whole arc from a consumer's intent to a
sovereign, audited, drift-checked realization — with neither locked to the other.

## Why they fit (the reasons)

1. **Independent convergence = near-zero impedance.** OSAC's public fulfillment model (Kubernetes-style
   `spec`/`status` + `conditions`, **JSON Schema 2020-12** validation, a **Template → CatalogItem →
   Instance** catalog, and `FieldDefinition{path,editable,default,validation_schema}`) is the same model
   UDLM arrived at independently — and the same one `enhancements#55` re-derived. Three designs, one shape.
   Integration that would normally be an adapter problem is a *mapping* problem.

2. **Complementary layers, no overlap.** OSAC stops where UDLM begins:
   | Concern | OSAC today | UDLM/DCM adds |
   |---|---|---|
   | Desired/observed state | `spec`/`status` + `conditions`, one live object + a version counter | **Four immutable states** (Intent→Requested→Realized→Discovered) with history |
   | Audit | reconciler-reported status | **AUD-001/002** synchronous, append-only, Merkle/RFC-9162 tamper-evident chain |
   | Drift | none first-class | **Discovered** state + drift detection |
   | Sovereignty/policy | placement within a site | **Governance Matrix**, sovereignty zones, accreditation, trust scoring |
   | Portability | OSAC fulfillment backends | a **vendor-neutral** Resource Type contract OSAC is *one* provider of |

3. **Same north star: sovereignty.** OSAC = *Open Sovereign AI Cloud*. UDLM/DCM's sovereignty machinery
   (Governance Matrix, immutable sovereignty fields, offline Compound-Document closure, no-central-runtime
   evaluation) is exactly what a sovereign cloud needs to prove residency, run air-gapped, and rehydrate in
   place. The DCM/UDLM sovereign-rehydration capability *is* an OSAC requirement.

4. **Both open, both neutral.** Apache-2.0, public repos, no vendor lock — clean to co-engineer and to bring
   to a neutral home (the community → CNCF flywheel).

## How they compose

**OSAC becomes a DCM Provider.** DCM owns the four state stores and the governance; OSAC's Fulfillment API is
the realization target.

```
Consumer intent ─► DCM: Intent (immutable)
                   DCM: Requested  (layers ⊕ policy ⊕ Governance Matrix / sovereignty filter)
                        └─► dispatch to OSAC Fulfillment (Cluster-F / BareMetal-F)
                   OSAC realizes ─► returns spec/status + conditions + metadata.version
                   DCM: Realized   (versioned snapshot from OSAC's status)
                   DCM discovery ─► Discovered (drift vs Requested)
                   Merkle audit chain spans all four states
```

UDLM Resource Type Specifications are the shared contract; OSAC's `Template`/`FieldDefinition` become UDLM
**base entities + Constraint Profiles (E1)**; OSAC's `conditions`/`metadata.version` feed UDLM **Realized**
state; OSAC's reconcilers feed **Discovered**.

## Concrete examples

**1 — A cluster, end to end.** A user orders `Compute.Cluster` (a UDLM type derived from OSAC's `cluster`
proto). DCM records **Intent**, assembles **Requested** (org defaults + sizing layer + policy), and — because
the request is `sovereign`-profiled — the Governance Matrix filters to in-jurisdiction OSAC fulfillment
backends. OSAC Cluster Fulfillment (RHACM + Hosted Control Planes) realizes it; its `status`+`metadata.version`
become DCM's **Realized** snapshot; DCM discovery reconciles **Discovered**. Every transition is a leaf in the
tamper-evident audit chain.

**2 — Sovereignty that can't drift.** The cluster's `sovereignty_zone` and `data_classification` are
`createOnly` (immutable) UDLM fields — a later change forces replace + re-evaluation, so the entity *cannot be
silently moved out of its zone*. The full type closure ships as one offline Compound Document, so a
disconnected sovereign OSAC site validates and **rehydrates in place** without phoning home.

**3 — A composite stack.** "App platform" = OSAC `BareMetalInstance` + `VirtualNetwork` + `Cluster` as a UDLM
**Composite Entity**. DCM builds the DAG from `depends_on`, OSAC fulfills each constituent, and binding fields
wire outputs (the cluster's API endpoint from the network's realized IP) — typed, contract-checked, not string
interpolation.

**4 — One catalog, many offerings.** OSAC's `ClusterCatalogItem` + `FieldDefinition` become a UDLM
**Constraint Profile** over the base `Compute.Cluster` type: "Dev cluster" (3 nodes, fixed region) and "Prod
cluster" (HA, sovereign region) are two profiles over one contract, each governed by DCM policy.

## The 1 + 1 > 2

- **OSAC gains:** lifecycle history, drift detection, tamper-evident audit, sovereignty governance, and
  provider-neutral portability (its catalog items become portable UDLM contracts, not OSAC-only).
- **UDLM/DCM gains:** a real, open, production-grade provisioning realization that *proves* the model end to
  end — the reference realization the whitepaper describes.
- **Customers gain:** capabilities out of the box and time-to-value — a governed, sovereign, audited
  self-service platform without building the substrate themselves.

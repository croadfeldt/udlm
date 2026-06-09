# The Holistic Realization Model — UDLM's place in it

_Foundational. Captured 2026-06-08. Master copy: `dav/docs/holistic-vision.md`
(mirrored in `dcm/docs/holistic-vision.md`). This file states the shared model and
where **UDLM** sits in it._

## The model

**Use Cases are the unit of desired outcome.** A Use Case is *realized* only when
**three foundational pillars** each support it:

- **Platform** — can the architecture/plan support the UC? (capabilities,
  specification, rules, context, execution). DCM is a reference realization.
- **People / Process** — is the organization, its people, skills, and processes
  structured and operating to support the UC? (operating model, org design, value
  streams).
- **Enablement** — is the consumer enabled to adopt, consume, and operate the UC?
  (adoption, change, skills transfer, operationalization).

> **Platform + People/Process + Enablement → realization of Use Cases → the holistic vision.**

Each pillar is a different **view of mostly the same data** (UCs ↔ gaps ↔
capabilities), evaluated by the same gap-analysis engine (DAV); only the **evaluation
target** and **ingestion method** change per pillar. Output is always: gaps →
prioritized capabilities → strategy + roadmap.

## UDLM's role: the substrate beneath all three pillars

UDLM models data **from intent to realization** in a realization-neutral, wire-compatible
way. In the holistic model, the pillars (Platform, People/Process, Enablement) are
*realizations*; UDLM is the **substrate that represents their data universally** so that
UC drivers, assessment inputs, gaps, capabilities, and roadmaps are exchangeable across
pillars and tools rather than trapped in any one of them.

**DAV is a UDLM realization — a peer to DCM** (decision 2026-06-08). DCM realizes UDLM
for *infrastructure* resources; **DAV realizes UDLM for architecture/capability
*knowledge*** (Use Cases, Capabilities, Taxonomy Terms, Gaps, Assessments, Findings).
Both emit UDLM-conformant Data. The capability catalog maps onto UDLM's four states —
**Discovered** = capabilities an assessment observes in the field; **Intent** = a
proposed capability/term; **Realized** = the curated canonical entry; the **gap** between
them = DAV's analysis. UDLM needs a new entity-type family for this knowledge domain
(current types — Infrastructure Resource, Composite, Process — are infra-oriented); that
type-family definition is the prereq for DAV's UDLM-conformant schema. See
`dav/docs/capability-catalog-design.md` (UDLM CONFORMANCE).

The model's spine — **intent (Use Cases / desired outcomes) → realization (the three
pillars)** — is exactly UDLM's "intent to realization" lifecycle. As People/Process and
Enablement ingestion methods are added (assessment outputs, Value Stream Mapping, etc.),
their data should conform to UDLM contracts so the cross-pillar gap analysis operates on
one coherent, universal substrate. UDLM stays realization-neutral: any pillar tool that
honors the contracts is a peer.

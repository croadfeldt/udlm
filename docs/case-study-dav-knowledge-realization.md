# Case Study — DAV as a UDLM realization in a non-infrastructure domain

_An effectiveness analysis: does UDLM's "realization-neutral universal substrate" claim
hold when a system in a domain UDLM was **not** designed around adopts it? Written
2026-06-08 from the DAV capability-catalog modeling exercise. Companion:
`dav/docs/capability-catalog-design.md` (UDLM CONFORMANCE), `holistic-vision.md`._

## 1. The test

UDLM claims to be a **realization-neutral** substrate: "any system conformant to UDLM
produces data that any other conformant system can read, interpret, and exchange." The
reference realization — **DCM** — manages **infrastructure resources** (VMs, IPs, VLANs)
through a provisioning lifecycle. That is UDLM's home turf, so DCM conforming proves
little about *universality*.

The hard test is a system in a **maximally different domain**. **DAV** is an
architecture/capability **gap-analysis engine**: it manages *knowledge artifacts* — Use
Cases, Capabilities, a Taxonomy, Gaps, Assessments, Findings — through a **curation**
lifecycle, not a provisioning one. Nothing in DAV is "provisioned." If UDLM models DAV's
core data *natively and without forcing*, that is strong evidence the abstraction is a
genuine cross-domain standard. This case study examines the mapping that emerged when we
went to model DAV's keystone — the capability catalog ↔ taxonomy — and asked "what is the
definition of Data in UDLM?"

## 2. Two realizations, opposite ends of the spectrum

| | DCM (reference) | DAV (this study) |
|---|---|---|
| Domain | Infrastructure resources | Architecture / capability **knowledge** |
| Entity examples | VirtualMachine, IPAddress, VLAN | Capability, TaxonomyTerm, UseCase, Gap |
| Lifecycle driver | **Provisioning** (a Provider builds it) | **Curation** (humans + LLM propose/normalize/accept) |
| "Realized" means | A provider confirmed it exists | A reviewer accepted it as canonical |
| "Discovered" means | A discovery run observed the live resource | An **assessment** observed the capability in the field |
| The core operation | **Drift detection** (Realized vs Discovered) | **Gap analysis** (canonical vs assessed) |

These are about as far apart as two domains get. That is exactly what makes the result
interesting.

## 3. The universal Data properties map directly

UDLM's `foundations.md` defines Data as "any structured artifact with a type, fields,
classification, provenance, and lifecycle state … always versioned, always identified by
UUID, always carrying provenance." Applied to a `Capability`:

| UDLM universal property | In DAV |
|---|---|
| **UUID**, stable across lifecycle | A capability keeps one id from "proposed" through "canonical" through "deprecated" |
| **Type** determines schema | `Capability`, `TaxonomyTerm`, `Alias`, `Antipattern` are distinct types with distinct field sets |
| **Lifecycle state** (per-type machine) | The curation/normalization state machine (below) |
| **Artifact-metadata block** (handle, version, status, owned_by, created_by, created_via) | handle = capability name; owned_by = the scope/tier; created_via = assessment ingest / UC analysis / manual |
| **Field-level provenance** | "this capability's `domain` came from the DCM taxonomy; its `evidence` came from assessment X, finding Y" |
| **Data classification** | Engagement-derived capabilities are client-confidential; the canonical taxonomy is public — per-field classification governs what crosses the boundary |
| **Contributor identity + review** | The hybrid LLM-proposes / human-curates step is UDLM's federated-contribution model verbatim |

No property had to be discarded or bent. The metadata block, provenance, and
classification are arguably a *better* fit for DAV than the bespoke columns we first
drafted — provenance and confidentiality are first-order concerns for a consulting
deliverable.

## 4. The key finding — the four states map onto knowledge curation

UDLM's four states were designed to track an infrastructure resource: **Intent** (what
was asked), **Requested** (what was approved/dispatched), **Realized** (what was built),
**Discovered** (what is observed now). The surprise is how cleanly they describe a
capability catalog that has nothing to do with provisioning:

| UDLM state | Infrastructure (DCM) | Capability knowledge (DAV) |
|---|---|---|
| **Intent** | The consumer's raw request | A **proposed** capability / taxonomy term (back-fill candidate) — "what we think should exist" |
| **Requested** | Policy-processed, provider-ready payload | The curated, review-approved proposal (the contribution under review) |
| **Realized** | Provider-confirmed resource | The **canonical** catalog entry / accepted taxonomy term |
| **Discovered** | What a discovery run observes live | What an **assessment** observes in the field (ephemeral, refreshed per assessment run) |

And then the operation falls out of the model for free:

> **DCM's drift detection (Realized vs Discovered for a VM) and DAV's gap analysis
> (canonical capability vs assessed capability) are the *same UDLM operation*.**

Both compare the authoritative "what should be" against the observed "what is," over data
with full provenance. DAV's entire value proposition — find the gaps between the target
architecture and the client's assessed reality — is UDLM drift detection applied to
knowledge. The **back-fill loop** (assessments surface capabilities the taxonomy lacks →
propose → accept → taxonomy grows) is UDLM's **drift remediation** loop: Discovered state
reveals what Realized state is missing, and remediation updates the canonical record.

That a model built for VM provisioning expresses capability curation this exactly is the
core evidence of UDLM's effectiveness: the four states are not really about
infrastructure — they are about **intent vs reality with provenance**, which is universal.

## 5. Where the mapping stretches (honest limits)

- **Requested** is the weakest analog. In DCM it is "dispatched to a Provider"; DAV has no
  provider provisioning a capability — the closest analog is the human/LLM curation-review
  step. The state is meaningful but its semantics are softened.
- The **operational states** (OPERATIONAL / SUSPENDED / decommission, drift-active) are
  infrastructure-physical. Knowledge artifacts have a thinner post-Realized life
  (deprecation ≈ decommission); there is no "SUSPENDED capability consuming resources."
- The biggest gap is **entity types, not the substrate.** UDLM's three primary types
  (Infrastructure Resource, Composite, Process) are infra-oriented; none fit a Capability
  or a TaxonomyTerm. **DAV needs a new knowledge entity-type family.**

This last point is the most useful finding for UDLM itself: **the universality lives in
the substrate and contracts (identifier, lifecycle, provenance, classification,
four-state, drift), not in the entity-type catalog.** Types are domain extensions layered
on a universal base. UDLM is "realization-neutral" precisely because a new realization is
expected to bring its own types while honoring the contracts — DAV is the proof that this
extension path works for a domain UDLM never anticipated.

## 6. The interoperability dividend

Because both DCM and DAV would emit UDLM-conformant Data, capabilities flow **across** the
boundary for free: a capability DAV identifies as "required by these use cases" is the
same UDLM artifact a DCM platform must "provide" — no translation layer. The consulting
back-fill (field engagements → taxonomy completion) compounds across clients *because it
is all one substrate*. This is the payoff UDLM promises — "data any other conformant
system can read" — demonstrated rather than asserted.

## 7. Verdict

UDLM passes a hard universality test. Modeling DAV on it is **principled, not forced**:
every universal Data property applied, the four-state model described knowledge curation
as naturally as it describes provisioning, and DAV's signature operation turned out to be
UDLM drift detection in a new domain. The one boundary is healthy and expected — entity
types are domain-specific extensions on a universal substrate. The recommendation that
follows: define a knowledge entity-type family in UDLM and make **DAV a first-class UDLM
realization, peer to DCM** — which both validates UDLM and gives DAV a consistent,
exchangeable data model it would otherwise have reinvented.

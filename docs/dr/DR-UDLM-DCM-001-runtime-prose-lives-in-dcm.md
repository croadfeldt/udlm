# DR-UDLM-DCM-001: UDLM is the data model; DCM is the realization — runtime-architecture prose belongs in DCM, not UDLM

**Status:** Proposed
**Realized by:** _not yet_ — decided, no machine surface.
**Type:** Decision Record — a project/process decision (`docs/spec/foundations/knowledge-family.md` §4.5); architecture decisions are ADRs (`../adr/`)

**Background — read first (the cold reader's on-ramp; skip if you have the context).** The surfaces this decision governs: `foundations/context-and-purpose.md` ·
`foundations/foundations.md` · `foundations/four-states.md` · `foundations/ownership-sharing-
allocation.md` · `docs/spec/contracts/data-store-contracts.md` ·
`docs/spec/contracts/information-providers.md` · `docs/spec/contracts/provider-contract.md` §10 (capability discovery)

## Context

pkliczewski's review across dcm-project/udlm #15-#18 repeatedly flags UDLM specification prose
that describes DCM's RUNTIME — the layer-assembly engine, the Policy Engine, provider
interfaces/protocols, processing and drift-detection mechanics, storage TECHNOLOGY choices,
and deployment — as belonging in DCM, not in the data model ('this is DCM architecture not
UDLM', 'part of implementation not data model', 'UDLM must define formats, structure of json
to describe infrastructure'). He is not asking for schemas to move OUT of UDLM — the opposite:
he asks repeatedly 'where are the types defined?' and wants MORE formal schema in UDLM. The
governing boundary this record ratifies: UDLM defines the DATA — the JSON formats, structures,
record schemas, entity/type/state vocabularies, and typed relationships — and NOTHING about
how a realization assembles, evaluates, stores, or deploys it. A UDLM spec MAY carry at most a
one-line 'consumed by DCM's X' reference where it makes the UDLM-carries / realization-does
boundary legible (the discipline already baked into the D8 registry schemas: 'UDLM carries the
record; DCM's Policy Engine evaluates it'), but the HOW-prose moves to DCM's architecture
docs. This preserves UDLM's implementation-agnosticism (a conformant realization need not be
DCM) and its adopt-by-reference posture, and it makes the specs reviewable by a data-model
audience rather than a DCM-internals audience.

## Decision

UDLM carries the data model, the record schemas, and at most one-line 'consumed by DCM's X'
consumer references. All prose that DESCRIBES a realization's runtime — assembly engine,
policy evaluation mechanics, provider invocation protocol, storage technology, processing
pipelines, drift-detection mechanics, deployment — moves to DCM's architecture documentation.
Provider DATA (adopted-standards support matrices, capability declarations) stays in UDLM;
provider INTERFACE/protocol (how DCM invokes a provider) moves to DCM. This boundary is a
review-checklist gate on every UDLM spec PR.

## Data · Policy · Provider

- **Data** — UDLM's entire normative surface is Data: entity/type/state/relationship formats
plus the registry/*.schema.json record schemas. Nothing about processing belongs here.
Cost/metering, host-network, server-baseline, etc. are all modeled as data or referenced as
external data — never as runtime behavior.
- **Policy** — The boundary is enforced by review, not by a machine gate — the PII-001/compat
CI gates cover tokens and version bumps, not prose. A UDLM spec PR that describes DCM
internals is out of scope and is bounced at review. Add 'no runtime-architecture prose' to the
UDLM spec-review checklist.
- **Provider** — Provider support DATA (provider-adopted-standards.schema.json, capability-
discovery capability declarations, information-provider registrations) is UDLM. Provider
INTERFACE/protocol (the wire contract for how a realization dispatches to a provider) is DCM.
Where a UDLM contract doc currently carries both, the interface prose moves and the data shape
stays.

## Alternatives considered

- **UDLM names zero consumers — strip every reference to DCM entirely (the strictest read,
e.g. CONFORMANCE:113, context:26)** — a data model that names no consumer is harder to review,
not cleaner — the UDLM-carries / realization-does boundary becomes invisible; reviewers cannot
see intent *Rejected:* sterility harms reviewability without serving agnosticism; the real
objection is DCM-INTERNALS prose, not a one-line consumer reference
- **Keep runtime-architecture prose in the UDLM foundations/contracts docs as-is** — couples
the normative data model to one realization; exactly that objection; makes UDLM un-adoptable
by a non-DCM realization *Rejected:* violates UDLM's core purpose as an implementation-
agnostic data model
- **UDLM = data + schemas + at-most-one-line consumer references; ALL runtime-architecture
prose moves to DCM (chosen)** — requires a prose-migration pass over the older
foundations/contracts docs that predate the D8 discipline

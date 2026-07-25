# UDLM ADR-045: Class evolution and pinning — atomic recompilation, two-plane pins, portability in the compat contract

**Status:** Proposed (croadfeldt upstream) — ratified in-session 2026-07-25, pending engineering review
**Date:** 2026-07-25
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)
**Related — the complete picture, each cited once.** The class system this governs (ADR-038 —
Base/Type/Provider Classes of SharedDataElements, portability derived from element scope), the
versioning doctrine it extends (VERSIONING.md — uuid is the revision, the handle is the thing;
any change mints a new uuid), the pin-behind precedent it generalizes (the estate's
type-version pinning: behind is legal, enumerated debt — never silent), the consumer surface
the blast radius reads (ADR-044 — consumers declare what they read), and the corpus that
measures it ([`use-cases/class-versioning/`](../../use-cases/class-versioning/README.md) —
cases 001–006 and 009 encode this ADR's rulings as testable contracts).

## Context

The class system makes every resource, process, and provider definition a composition over
shared elements. That concentration is the point — one Base element serves dozens of
descendants — and also the risk: a Base change ripples into every Type Class, Provider Class,
and generated flat spec built on it. Software inheritance met this as the fragile-base-class
problem and never fully solved it, because behavioral compatibility is undecidable. Ours is
decidable: classes are data contracts, descendants are compiled artifacts, and the ripple is a
computable set. The questions to settle are when recompilation happens, where version pins are
legal, and what "compatible" means when the thing that changes is not a schema shape but an
element's scope.

## Decision

**1. Recompilation is atomic.** A class change and every regenerated descendant — Type
Classes, Provider Classes, generated flat specs — land in one change set. Each regenerated
artifact mints a new uuid and a version bump the compat gate accepts as sufficient. Lazy
regeneration is rejected: it would let one release carry two truths of the same element, which
is version skew inside a single source. The cost — Base changes produce large diffs — is
accurate reporting, not overhead: a Base change is large, and the diff is where its size
should be visible.

**2. The blast radius is machine-enumerated, never hand-listed.** A class change carries the
computed set of affected artifacts, derived from the class graph, plus the downstream
consumers that will accrue version debt, derived from the ADR-044 manifests. The enumeration
is part of the durable change record.

**3. The software-industry mapping is adopted: the registry is the library, an organization's
estate is the application.** Libraries declare compatible ranges and never pin; applications
pin exactly and own their upgrades. Concretely:

- **Intra-registry references are by handle only.** A Type or Provider Class that pins a fixed
  Base version inside the registry is refused at validation — the registry ref (commit) is the
  sole intra-registry pin, and it pins everything at once.
- **Organization-edge pins are first-class and uuid-precise.** The uuid IS the revision, so a
  pin is exact by construction. A pinned estate compiles and realizes against the pinned
  revision completely; nothing upstream propagates until the organization re-pins.
- **Pin-behind is legal, enumerated debt.** The version distance appears per pinned artifact
  in the estate's own validation output and re-opens when the estate's registry ref advances —
  the standing estate discipline, applied unchanged to classes. **Pin-ahead or
  pin-to-nonexistent is refused**, typed distinctly from legal debt (the ADR-044
  `noted_version` rule, generalized).

This dissolves the apparent conflict between organizational control and the versioning model:
the model never forbade consumer-edge pinning — it forbids being *silently* behind. Complete
control and complete visibility are the same mechanism.

**4. Element scope is part of the compatibility contract.** Portability is derived from scope
position (ADR-038), so moving an element to a narrower scope (Base → Type, Type → Provider)
shrinks the portable surface of every carrier — a **breaking** change even when no schema
shape changes, classified by rule, not review judgment. Scope widening is compatible. No
schema differ can see this class of break; the compat gate must implement the scope rule
explicitly.

**5. The inheritance depth stays at three.** Base/Type/Provider is a ruling, not a habit —
ripple cost grows with depth, and the three scopes are exactly the portability distinctions
the model needs. A proposed fourth level is a re-review trigger for this ADR.

## Consequences

- Every Base change re-proves all descendants mechanically: atomic recompilation means the
  instance-fuzz, composition, and compat gates run against every regenerated spec in the same
  commit — the class system inherits the whole deterministic hammer suite with no new tests.
- Registry evolution stays honest: blast radius in the change record, debt in the estate's
  output, nothing silent anywhere in the chain.
- Organizations can be arbitrarily conservative without forking: a fully-pinned estate is a
  supported state whose cost is a visible debt list, and ADR-046's blue/green contract is the
  instrument that retires the debt with evidence.
- Gate work this creates (realization-plan P0): the class-compat classifier (including the
  scope rule), the blast-radius enumerator, and pin resolution validation on both planes.

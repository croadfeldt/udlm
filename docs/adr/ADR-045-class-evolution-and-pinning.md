# UDLM ADR-045: Class evolution and pinning — atomic recompilation, two-plane pins, portability in the compat contract

**Status:** Proposed (croadfeldt upstream) — pending engineering ratification (#217); decided 2026-07-25
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

The class system rebuilds every resource, process, and provider definition as a composition
over shared building blocks, arranged in three levels: Base elements everything in a category
shares, Type elements multiple providers support, and Provider elements specific to one
engine. That concentration is the point — one Base element serves dozens of descendants — and
also the risk: a Base change ripples into every Type Class, Provider Class,
and generated flat spec built on it. Software inheritance met this as the fragile-base-class
problem and never fully solved it, because behavioral compatibility is undecidable. Ours is
decidable: classes are data contracts, descendants are compiled artifacts, and the ripple is a
computable set. The questions to settle are when recompilation happens, where version pins are
legal, and what "compatible" means when the thing that changes is not a schema shape but an
element's scope.

## Decision

**1. Recompilation is atomic.** A class change and every affected descendant land in one
change set: **generated flat specs regenerate**; **authored Type and Provider Classes
revalidate**, rotating uuid and version only where their own content actually changes (the
rotation gate's no-op rule holds — an unchanged authored file never rotates). Every artifact
whose content changes mints a new uuid and a bump the compat gate accepts as sufficient — which
pre-1.0 means the **MINOR floor** for breaking classifications (VERSIONING.md, "the pre-1.0
bump floor"), never a REVISION and never a jump to 1.0. Lazy
regeneration is rejected: it would let one release carry two truths of the same element, which
is version skew inside a single source. The cost — Base changes produce large diffs — is
accurate reporting, not overhead: a Base change is large, and the diff is where its size
should be visible. Atomicity is **registry-internal** — consistency of the source, never
propagation: estates, pins, and realized instances are untouched (Decision 3; §8
realized-instance stability) and encounter the change only as surfaced blast radius and
visible debt, adopted under their own change policies (the operational response matrix).

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
  pin is exact by construction. The revision store is the registry's git history: a pin
  resolves within the registry ref (or ref range) the estate declares it consumes — which is
  how behind-but-legal and unknown-refused are mechanically distinct. A pin carrying both
  `version` and `uuid` must carry a matching pair; a mismatch is refused, and the uuid is
  authoritative. A pinned estate compiles and realizes against the pinned revision completely;
  nothing upstream propagates until the organization re-pins.
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

**5. The inheritance depth stays at three scope planes.** Base/Type/Provider is a ruling,
not a habit — ripple cost grows with depth, and the three scopes are exactly the portability
distinctions the model needs. This caps the **class-hierarchy planes**, and is orthogonal to
ADR-038's naming-depth rule ("unbounded, but governed"), which governs **dotted address
depth** within elements — both stand; neither supersedes the other. A proposed fourth scope
plane is a re-review trigger for this ADR.

**6. Ruled edge cases.**
- **Element deletion** is breaking (the VERSIONING.md remove-a-field row), handled by the same
  atomic path as narrowing: one change set, blast radius enumerated, MINOR-floor bump pre-1.0.
- **Pins are subtree-consistent.** Pinning a class pins its ancestor chain; two pins in one
  estate that resolve the same ancestor to different revisions are refused — the intra-registry
  two-truths ban, applied at the estate edge (no diamond skew).
- **A shared artifact resolves under exactly one pin set** — its owning estate's. Consumers in
  differently-pinned estates read the owner's compiled-against record; they do not re-resolve
  it under their own pins.

**7. Provenance is declared, verified, and two-plane.** Every generated flat spec carries a
compilation-provenance block naming the exact revisions (handle, version, uuid) of every input
— Base, Type, and Provider classes, shared-element layers, referenced common schemas, and the
generator version — so "the artifact contains its chain" is verifiable, not asserted. Every
realized instance extends this with realization provenance: the provider definition/
registration revision and engine binding version that realized it. Live provenance means the
current artifact states its inputs; historical provenance means any past revision's full chain
reconstructs mechanically from the revision store (immutable uuids make history a database).
Provenance is only worth carrying if verified: recompiling from the block's named inputs must
reproduce the artifact byte-comparably, and a mismatch (a hand-edit after generation, a stale
block) is refused at the gate as an integrity failure. Corpus: class-versioning 010–012.

**8. Providers version their edge, and only their edge.** A provider's declared surface — the
capabilities it registers, the standards it adopts, the defaults it publishes, and the outputs
it populates per type — is a versioned contract under exactly the standard rules: additive
surface changes are compatible, removals and shape changes are breaking, the same bump floors
apply, and any change to the definition rotates its uuid. Past the naturalization boundary
(dcm ADR-023 — where provider-native implementation begins), the provider is free: engine
internals, dependencies, and implementation may change without any versioning obligation
toward consumers, because nothing a consumer can bind to has changed. The seam is precise:
an internal change that alters a populated output's observable shape *is* a surface change and
versions accordingly. Individual capabilities remain their own accreditation/version units
(ADR-004), nested within the definition's version; the engine binding version a realization
actually used is recorded in realization provenance (§7). Pins, debt, and blue/green promotion
apply to provider definitions unchanged — an estate pins a provider definition revision the
same way it pins a class revision, and an engine upgrade verifies by output diff (the
process-migration stage's engine-upgrade-regression pattern).

Provider versioning is **two-plane** — the registry's own pattern (individually versioned
types, whole-release pinned by ref), recurring: **capabilities version individually** as the
contract unit consumers bind to, and the **provider definition revision (uuid) is the
whole-surface pin**. All compat classification routes to the capability plane: a breaking
change inside one capability majors *that capability* and reaches exactly the consumers bound
through the types it covers (`covers_types` — the explicit capability↔type linkage), never
churning consumers of the provider's other capabilities. The **envelope version carries set
semantics only**: capability added = minor, capability removed = major, provider-wide
defaults/standards on their own merits — a member's internal breaking change does not major
the envelope, because the set did not change. Consumers bind and pin at the finest unit they
consume (the capability, by `capability_uuid`); estate-wide conservatism pins the definition
revision. Realization provenance (§7) records the **capability revision** that governed a
realization alongside the definition revision and engine binding. The operational payoff is
**capability-level blue/green**: one capability's v2 runs green under ADR-046's promotion
contract while sibling capabilities keep serving on their current versions — staged provider
evolution without whole-provider upgrades. **Realized instances are stable under capability movement.** A capability version change —
compatible or breaking — never triggers a redeploy, update, or reconciliation of instances
already realized under an earlier capability revision: realization provenance is immutable
fact, and a running instance's contract is the revision that governed its realization. The
movement is *surfaced* at instance level (realized-under vs current-capability distance, typed
distinctly from spec pin-lag) and the organization's change policy decides — update, re-realize
under the new revision (blue/green when breaking), or deliberately nothing, which is
legitimate. Breaking-ness matters at the *next* realization, never retroactively to a running
one. The industry's own version of this rule is building codes: a house built to the
2019 code is not upgraded when the 2022 code publishes — once built, the object has a life of
its own — but a *renovation* is where current-code adoption gets decided. Mapped here:
**every voluntary touch — a day-2 change, a rebuild, a re-realization — is a declared decision
point.** The system surfaces the instance's provenance-distance at the touch; the estate's
policy decides whether the touch adopts current revisions, offers the choice, or proceeds
under governing provenance; all three are enabled, recorded outcomes. The touch-trigger stance
(adopt-on-touch, offer-on-touch, provenance-until-explicit) is a policy clause like any other
— declared once, never improvised per touch. The analogy has two faces and both are
load-bearing: the house's protection from the new code is one; the other is that the code's
publication is **surfaced the day it lands** — the owner always sees the distance, and "not
until renovation" is a decision the owner *makes and records* (the provenance-until-explicit
stance, declared), never a default that happens by silence. Surfacing is continuous; deciding
is always available — an organization may adopt between touches whenever it chooses; the touch
is simply the moment the system re-asks the question instead of the calendar. Three rules make this stability real rather than aspirational: **mixed-version
operation is supported by contract** — a capability's day-2 verbs (update, resize, snapshot,
delete) must keep operating instances realized under any of its non-retired revisions, so a
1.2.0-realized instance is operable while current is 1.3.0; **realized instances are pinned
consumers** — a capability revision with instances realized under it cannot retire without the
published deprecation window, making retirement the one legitimate, calendared forcing
function; and **drift compares against provenance, never against current** — reconciliation
that measured a 1.2.0-realized instance against the 1.3.0 contract would manufacture phantom
drift fleet-wide and "fix" it into exactly the mass redeploy this rule forbids. Accreditation stays at the capability (ADR-004),
untouched by the envelope. Corpus: class-versioning 013–020.

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

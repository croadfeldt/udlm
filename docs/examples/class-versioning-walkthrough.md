# Worked example and how-to: evolving, pinning, and re-pinning classes

**What this settles:** how ADR-045 (class evolution and pinning) and ADR-046 (blue/green
promotion) work in practice — one worked scenario end to end, then the how-tos an engineer
reaches for. Every section is backed by a corpus case (`use-cases/class-versioning/`), and
those cases ride every normal analysis run like the rest of the corpus — the documentation and
the validation share one source of truth.

The running example: Base Class `Compute` carries a `memory` element (a Quantity object) that
every compute descendant — VirtualMachine, Container, BareMetalHost — includes at Base scope.

## The worked scenario: one element, three changes

**Change 1 — additive (UC-001).** The maintainer adds an optional `hugepages` sub-property to
the `memory` element. One change set carries: the Base Class edit, every regenerated Type and
Provider Class, every regenerated flat spec — each with a new uuid and a minor/patch bump —
and the regeneration manifest. The fuzz, composition, and compat gates re-prove every
descendant in the same commit; no hand-written test exists anywhere in this flow. A pinned
downstream estate sees nothing: its pins resolve the old revisions until it chooses otherwise.

**Change 2 — breaking, under-declared (UC-002).** The maintainer changes `memory.size` from
string to object and declares a revision bump. The compat gate refuses (real output format —
the pre-1.0 floor for a breaking classification is MINOR, per VERSIONING.md):

```
  [major] changed type on 'memory.size' (string -> object)
  required bump: MAJOR   declared bump: REVISION   [pre-1.0: MAJOR relaxed to MINOR]
FAIL: a MAJOR-classified change needs at least a MINOR bump pre-1.0 (0.4.1 -> 0.5.0)
```

Nothing regenerates from a refused change. The same classifier refuses a *scope narrowing* —
moving `memory` from Base to Provider scope — even with no shape change at all, because every
descendant's derived portable surface would shrink (UC-009).

**Change 3 — breaking, properly declared (UC-003).** Declared major. The change record now
carries the machine-computed blast radius: every class carrying `memory`, every regenerated
spec, and — via the ADR-044 consumer manifests — every downstream consumer that will accrue
version debt when this ships. Review reads impact, not diffs-archaeology.

## How to pin (organization edge) — UC-005

Pin uuid-precise in the estate's class configuration; the uuid IS the revision, so the pin is
exact by construction:

```yaml
class_pins:
  - class: Compute                # the handle names the thing…
    version: 0.4.1                # …the version communicates intent…
    uuid: 2f6c1a9e-...            # …the uuid IS the pinned revision
```

The estate compiles and realizes against the pinned revision completely. The cost is a debt
line, not a capability:

```
PIN-BEHIND (legal): Compute pinned 0.4.1 (2f6c1a9e); registry current 1.0.0 — 1 major behind
```

The list re-opens whenever the estate's registry ref advances. Two things are refused, typed
distinctly (UC-004, UC-006): a *registry-internal* class declaring a fixed-version parent
(intra-registry references are by handle; the registry ref is the only internal pin), and an
estate pin naming a revision the consumed registry ref does not contain.

**Does an upstream class change affect my pinned resource?** No — and not because the chain is
separately locked, but because your pinned artifact *contains* its chain: the flat spec was
compiled from its Base/Type/Provider classes at a specific registry state, and that content is
baked in at compilation, not looked up live. Upstream changes mint *new* revisions (uuids are
immutable; old ones never retire); yours is untouched by construction. The only thing that
changes on your side is the debt list — the new revision appears as visible lag until *your*
change policy says adopt, through blue/green. And if you pin at the class level instead, the
ancestor chain pins with it (subtree consistency, ADR-045): there is no half-locked chain.
Corpus-tested: UC-001 ("every pin still resolves to its pre-change uuid") and UC-005 ("no
registry change alters the estate's behavior until the organization re-pins").

## How to re-pin with blue/green — UC-007/008

Never re-pin on the compatibility claim; re-pin on the diff:

1. Compile the estate's intent corpus twice: blue = current pins, green = candidate revisions.
2. Dry-run realize both; diff the **declared typed outputs** (never provider internals).
3. Empty or fully-approved diff → promote: pins advance atomically, debt entries close, the
   diff + approvals persist as the promotion's attestation evidence.
4. Dirty diff → promotion refuses with the diff as the typed reason, the estate stays fully on
   blue, and the contradicted compatibility claim routes to the registry as a finding with
   your diff as provenance. Your caution upstream becomes everyone's validation.

The same procedure serves a provider swap (EngineBlue → EngineGreen): hold the Base/Type
elements constant, vary the one axis, diff the outputs. One mechanism, both migrations.

## What to remember

- **Registry = library, estate = application.** Inside the registry, by-handle references and
  the registry ref as the single pin. At your edge, pin exactly, see your debt, retire it with
  evidence.
- **A refusal is never a dead end.** Every refusal in this flow is typed and names its fix:
  the required bump, the by-handle correction, the unresolvable pin, the offending diff.
- **Thin outputs weaken your safety net.** The blue/green diff can only compare what types
  declare — if a type you depend on declares one boolean, demand a better output surface
  before trusting a promotion over it.

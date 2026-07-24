# Class-system realization — the program plan

**What this settles:** the execution plan for the maintainer's ruling (2026-07-25): *the
portability we want requires moving resource types AND provider types onto the class system.*
ADR-038 decided the model (Base → Type → Provider Classes of `SharedDataElement`s, Liskov
extension, all tiers instantiable, promotion); this plan realizes it — phased, compat-preserving,
gate-ratcheted. Ratification note: ADR-038 is Proposed pending the engineering pass (#217); this
plan executes the decided model and inherits that status.

## The compat-preserving core decision

**Classes become the authoring layer; the flat type specs become generated artifacts.**
A class artifact (`registry/classes/`) composes `SharedDataElement`s; a generator compiles each
Type Class into exactly the flat spec shape consumers read today (same meta-schema, same wire
contract, `--check`-gated like TYPE-CATALOG). Nothing downstream breaks on day one; consumers cut
over to class-aware reads (SDK #222) at their own pace. This is the same generated-not-hand-edited
pattern that already governs the catalog — applied to the registry itself.

## Why this yields the portability we want

An element's **scope position is its portability** — no declaration needed:
- element on the **Base Class** (`Compute`) → portable across every type in the category
- element on the **Type Class** (`Compute.VM`) → portable across every provider of the type
- element on a **Provider Class** (`Compute.VM.OCPVirt`) → provider-bound, by construction

The realized-entity `portability` block stops being asserted and becomes **derived** from where an
instance's populated elements sit — same move as derived shape (`has_constituents`) and derived
nature (`edge_type`): compute, never store what structure already says. Promotion (moving an
element up a class, rule-36/ADR-038 governed) *is* the portability-improvement operation, and it
becomes visible in diffs.

## Priority signal — automation intent (maintainer, 2026-07-25)

**The Process family is likely the most-used instance of the class model.** Platform-to-platform
automation migration (the Chef→Ansible render) is a live, recurring need in a way that
resource-provider migration is episodic — so **automation intent is a first-class peer of
resource intent**, and the Process family may lead class-system adoption rather than follow it.
Open sequencing question for the maintainer at P1: pilot on Compute (deepest inheritance, most
types), on Process (highest usage, sharpest payoff), or both in one cycle (Compute proves depth,
Process proves the multi-provider declaration).

## Phases

**P0 — substrate.** Meta-schema gains `SharedDataElement` + the class-artifact schema
(`registry/classes/*.yaml`: class id, parent, elements[], adopts). `validate_registry` gains the
Liskov gate (a child class adds or refines, never contradicts its parent) and dotted-address
resolution (`compute.vm#memory` → the owning class + element). The spec generator lands with
`--check` in CI. *Evidence this is ready: the class renders in this directory (compute, identity)
were authored against exactly this shape.*

**P1 — pilot: the Compute category.** Author Base Class `Compute`; re-express the Compute.* types
as element compositions; the generator reproduces their current 0.x specs byte-comparably (bump
only where the pilot fixes a real defect). First promotions — the proven cross-type elements this
week surfaced: `firmware`/`boot_mode` (VM 0.6.0 vs BareMetalHost 0.6.0 — flagged as a convergence
candidate in both PRs), desired-power (`run_state.desired_state` / `online`), the capacity
Quantity patterns, `Identity` discriminators. One category proves the path before the fleet
commits.

**P2 — fleet migration.** Remaining categories, one PR per category seam (≤3k lines each), each
burning its types' G3/consistency residue on the way through. common-elements §2.x shapes migrate
to Base-tier SharedDataElements where they are truly cross-category (Quantity, Reference stay
meta-level).

**P3 — Provider Classes registered.** Provider registration declares the provider's Class — the
element sets it adds per Type Class (the surface `provider_extensions` retirement pointed at;
provider-contract §8 profiles reference it; dcm ADR-025 is the engine half). The estate and DAV
corpus provider-class UCs (hammer-recent-model) become executable against real registered classes.

**P4 — derived portability.** The realized-entity `portability` block re-keyed onto element scope
positions (computed; consumer-notification discipline unchanged). The declared classification
survives one MINOR as a cross-check (declared vs derived mismatch = a finding), then retires —
the provider_extensions playbook, applied gently.

## The Process family classes too (maintainer refinement, 2026-07-25)

**The Process family is a class model — shallower inheritance, same three tiers, and the
multi-provider shared capability is its headline payoff.** The layering is symmetric with
Resources once definition and instance are kept straight (no *instance* classes anywhere — a run
instantiates a class exactly as a VM instance does):

- **Base tier (thin, but real):** the execution contract every process shares — typed
  inputs/outputs, idempotency declaration, timeout/retry semantics, compensation declaration,
  affected-entities declaration. Shallow is not absent: this tier is what makes any process
  governable by the same policy machinery.
- **Type tier — the shared capability:** `Process.OSPatch`-class definitions of *what the process
  does* (parameters, preconditions, declared effects), which **multiple providers declare support
  for** — exactly as multiple providers declare a resource type. Process execution enters the same
  selection machinery: placement chooses an engine the way it chooses a VM provider, and "can this
  automation run somewhere else" becomes the same computable question as resource portability.
- **Provider tier:** the engine binding — the Type realized as an AAP job template, a Tekton
  pipeline, a provider-native workflow — plus engine-specific elements. Engine lock-in is visible
  as element scope, like everywhere else.
- **Runs are instances** of the Type Class realized by the selected provider; Discovered-state and
  audit machinery apply unchanged.
- **Workflows are the composite shape** of Process types (the model already defines composite
  Process as DCM-sequenced constituent calls) — and they are **multi-family by reference, not
  containment**: their elements reference into Resource/Knowledge/Access class trees via the
  existing edge model. P0's meta-schema must permit class elements whose reference targets live in
  another family's tree; nothing else is invented.

## Gates and corpus

Each phase lands with its rule-36 kit: the Liskov gate and generator `--check` join CI in P0; the
existing portability UCs (uc-18 pair, hammer-recent-model, binding-surface) get class-aware
success criteria in P1; a `class-system/` UC set covers promotion, Liskov violation rejection,
and derived-portability drift by P4.

## Sequencing

After the current fix wave (it is quietly preparing this migration — every Reference and output
conversion carries over 1:1 as elements). P0+P1 are one focused cycle; #199's private-networking
Provider-Class element becomes P3's first worked example rather than a special case.

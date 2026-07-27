# How class versioning was decided — the story behind ADR-045 and ADR-046

**What this settles:** the narrative record of the class-versioning decisions — what the
question was, how it was worked, what was ruled, and what the process caught along the way.
The binding contracts live in ADR-045 (evolution and pinning) and ADR-046 (blue/green
promotion); this brief is the version a reader who wasn't there starts with. It is also the
reference exemplar for DOC-001 (CONTRIBUTING.md): every document in this repository is
written to be readable at this level.

## Background

UDLM is a registry of resource type definitions — virtual machines, networks, storage,
processes — that describe infrastructure *intent*, which providers then realize. Definitions
are moving from standalone hand-written specs onto a **class system**: shared building blocks
arranged in three levels — Base elements everything in a category shares, Type elements
multiple providers support, Provider elements specific to one engine. The payoff is
portability: where an element sits in that hierarchy *tells you* whether a workload can move
between providers, with no separate declaration to maintain.

## The question

Shared building blocks concentrate risk. If a Base element changes, everything built on it is
affected — the same "fragile base class" problem software engineering has fought for decades.
So: what happens downstream when a base changes? Do the registry's normal versioning rules
apply? Should an organization be allowed to pin itself to an old version for stability, even
though that appears to fight the versioning model? And how does testing make an upgrade off a
pin safe rather than a leap of faith?

## What was decided (five rulings)

1. **Changes ripple atomically, with the impact computed.** When a shared element changes,
   everything affected is rebuilt and re-verified *in the same change* — no lag, no partial
   states — and the full impact list (affected classes, regenerated specs, downstream
   consumers who fall behind) is computed automatically and attached to the change record. All of this happens
   **inside the registry** — it is consistency of the source, not propagation to consumers:
   estates, pinned artifacts, and running instances are untouched (rulings 2–3) and meet the
   change only as surfaced impact and visible debt, adopted under their own change policies.
   Registry-internal atomicity is what *makes* surface→decide→enable possible downstream — a
   lazily-recompiled registry would offer estates version skew instead of one coherent picture
   to measure their distance against.
2. **The registry is a library; an organization's estate is an application.** The industry's
   proven split, adopted whole: inside the registry, references always track current and the
   release commit is the only pin; at an organization's edge, pins are exact (down to the
   published version, or the content digest where bytes must be proven — ADR-051) and the
   organization owns its upgrades.
3. **Pinning old versions is fully supported — because the versioning model never forbade
   it.** What the model forbids is being *silently* out of date. A pinned organization keeps
   complete control, and its lag appears as an explicit, per-artifact debt list that reopens
   whenever it takes a newer registry snapshot. Control and visibility are the same mechanism.
   The same holds for what pins protect: a realized object has a life of its own — a house
   built to the 2019 building code is not upgraded when the 2022 code publishes. A
   *renovation* (any voluntary touch: a change, a rebuild) is where current-code adoption gets
   decided, and the organization's policy — not the platform — makes that call at the touch,
   with the staleness surfaced right there. Both faces of the analogy carry weight: the
   house is protected from the new code, *and* the owner saw the new code the day it
   published — "not until renovation" is a decision made and recorded, never a silence; the
   owner may also choose to update between renovations at any time, because the distance is
   always visible and the decision is always theirs.
4. **Portability is part of compatibility.** Moving an element to a more provider-specific
   level is a breaking change even if its schema shape is untouched — because it shrinks what
   is portable, and no ordinary schema comparison can see that. The rule is enforced by the
   compatibility gate, not by reviewer vigilance.
5. **Upgrades off a pin go blue/green, and evidence beats claims.** The same workload
   definitions compile under the old and candidate versions side by side; declared outputs are
   compared mechanically; promotion happens only on a clean (or explicitly approved)
   comparison, with the evidence preserved. A dirty comparison refuses the upgrade *and* sends
   the evidence upstream — "this claimed to be compatible and wasn't" becomes a bug report
   with proof attached, closing a loop the software world's package ecosystems never closed.

## How it was worked — use cases first

The scenarios were written before the decision records: nine corpus use cases
(`use-cases/class-versioning/`), four describing what must work and five that succeed only if
the system correctly *refuses* — an under-declared breaking change, an illegal internal pin, a
pin to a nonexistent revision, a promotion over a dirty comparison, a portability-shrinking
scope move. The decision records were then written to match the scenarios, and the whole
package was put through three independent adversarial reviews before it settled.

## What the reviews caught

The strongest find was a bug in the *existing* tooling, unrelated to classes: the
version-compatibility checker never noticed when a field's declared data type changed — a
breaking change (string to object) could pass as trivial, or with no bump at all, and the
package's own walkthrough had claimed otherwise. It was fixed and verified before the package
settled. The reviews also forced one answer where three documents had disagreed on how large a
bump a breaking change needs; surfaced that the "every change mints a new identifier" rule —
which the pinning design depends on — was written down nowhere official (it is now, in
VERSIONING.md); and caught that two use cases were unimplementable until the design said
where pinned old revisions actually live (the registry's git history).

## Where it stands

The realization plan's first phase carries the gates these rulings require — the
compatibility classifier with the scope rule, the impact enumerator, pin validation on both
planes, and two new record schemas (the regeneration manifest and the finding-routing record).
The blue/green harness lands with the pilot migration. Enforcement today is honestly zero of
eleven refusal scenarios — expected, since the specs and gates land in a planned sequence —
and the corpus cases ride every normal analysis run, so the distance between what is written
and what is enforced stays measured rather than assumed.

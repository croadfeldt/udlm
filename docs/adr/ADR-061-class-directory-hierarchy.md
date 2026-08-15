# UDLM ADR-061: The classes directory mirrors the class hierarchy — a verified projection

**Status:** Proposed (croadfeldt upstream) — **requires engineering ratification**; maintainer decision 2026-08-04
**Realized by:** _not yet_ — decided, no machine surface.
**Date:** 2026-08-04
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)

**What this settles:** where a class artifact lives on disk and what its path may claim — the
layout template, the naming rule, and the gate that keeps the path an honest projection of the
record.

**Background — read first (the cold reader's on-ramp; skip if you have the context).**

- **ADR-038**: the scoped-Class hierarchy — Base → Type → Provider tiers, dotted names, scope
  position is portability. This ADR gives that hierarchy its filesystem shadow.
- **The Automation/Job rulings (2026-08-04, on the ADR-038 addendum's line):** family
  (`Resource`, `Process`) is the reserved higher-order axis above categories; `Job` is an
  instantiable childless base. Both shape the layout below.
- **ADR-051**: versions live in records and the pin manifest, never in paths — why this layout
  has no version directories (the k8s `apis/<group>/<version>` pattern solves an evolution
  problem UDLM handles via the publish law instead).
- **DRV-001**: a stored copy of a derivable value is drift waiting to happen — why the path,
  which restates record facts, must be gate-verified.

---

## Context

Class artifacts accumulated as a flat directory of dotted filenames. At seven files it read
fine; at the ~50 the bulk conversion brings, a flat listing hides the structure the artifacts
exist to express. The class hierarchy is bounded (family + three tiers), which makes the
package-directory template — the most battle-tested "hierarchy as filesystem" pattern (Java
packages, Go modules, DNS zones) — applicable without its deep-nesting pathologies.

## Decision — the layout

**`registry/classes/<family>/<segments-as-path>.yaml`** — a class file sits inside its
parent's directory, named by its own segment:

```
registry/classes/
├── resource/
│   ├── compute/
│   │   ├── _base.yaml                Compute            (base — index file)
│   │   ├── vm.yaml                   Compute.VM         (type, leaf)
│   │   └── bare-metal-host.yaml      Compute.BareMetalHost
│   ├── hardware/_base.yaml …         (every category: a directory owning its _base.yaml + types)
│   └── topology/_base.yaml                     Topology           (childless instantiable base — uniform:
│                                                          still a directory, per the ruling)
├── process/
│   ├── automation/
│   │   ├── _base.yaml                Automation
│   │   └── ospatch/
│   │       ├── _base.yaml            Automation.OSPatch (type WITH providers → indexed)
│   │       ├── engine-blue.yaml      …EngineBlue        (provider, leaf)
│   │       └── engine-green.yaml
│   └── job/_base.yaml                Job                (childless base — uniform directory)
└── access/
    ├── access/_base.yaml + identity-escrow.yaml
    └── identity/_base.yaml + group.yaml, person.yaml, service-account.yaml
```

The rules:

1. **First path component = `lower(family)`.** Family is the grouping axis, not a tier; it
   appears in the path exactly once.
2. **Index-file template (maintainer ruling 2026-08-04, superseding the sibling-pair draft):**
   a **base is always a directory holding `_base.yaml`** — childless bases included (Job,
   Topology), uniformly. A **type or provider class is a leaf file** named by its own
   kebab-cased segment **until it has children**, when it too becomes `<segment>/_base.yaml`
   (OSPatch, having engines, is indexed; VM, having no providers yet, is a leaf). One
   directory owns everything about a class.
3. **Each dotted segment of `resource_type` is one path component.** Provider tier needs no
   special case — it is simply the third level. Segment casing follows the file-naming
   standard: word boundaries hyphenate (`bare-metal-host`), acronym runs merge (`ospatch`,
   `vm`).
4. **No version directories** (ADR-051 owns versions) and **no tier directories** — tier is
   derivable from depth and declared in the record.
5. Accepted cost of the template: a class **moves** (`<segment>.yaml` →
   `<segment>/_base.yaml`) when it gains its first child — a `git mv`, never a version event.

## Decision — the path is a verified projection, never a source

The path restates facts the records own (`family`, `resource_type`, `parent`) — a second
statement of hierarchy truth, which is precisely the drift class DRV-001 names. It is
admitted **only because it is gated**: `tests/check_class_paths.py` (`CLS-PATH-001`, CI +
signoff) verifies that every class file's path equals `lower(family)` + its kebab-cased
segment chain, and that the declared `parent` equals the directory ancestry. Records remain
the sole source; the path is navigation. A mismatch is a hard failure, and the gate is
negative-probed (a misplaced file is caught).

## Usage

- **Adding a class:** place the file where its name says it lives; the gate refuses anything
  else. A new category base is a new file directly under its family; its types arrive in the
  matching directory.
- **Browsing:** ancestors are the path; offerings are a directory listing. The parked
  family-prefixed referential coordinate (`Process.Automation.OSPatch…` — "more on that
  later") has its filesystem shadow here for free.
- **Tooling:** loaders read record content and glob recursively; nothing may parse meaning
  out of paths except the gate itself.
- **Moves are `git mv` only** — paths carry no identity ($id/uuid/version untouched), so a
  re-layout is never a version event.

## Data · Policy · Provider

Authoring-surface organization only: Data-side convention + gate. Policy and Provider are
untouched — nothing downstream reads class paths.

**Family-segment dedup.** When a class's first name segment equals its family (the `Access.*`
category under family Access), the directory is not repeated — the family directory *is* that
segment's directory: `classes/access/_base.yaml` (the Access category base),
`classes/access/identity-escrow.yaml`. `CLS-PATH-001` computes the deduped path; `access/access/`
is never legal.

## Consequences

- The bulk conversion lands its ~45 type classes into this shape from birth; family
  directories make the later factoring waves (scope promotion) visible as file moves up a
  level, gated the whole way.
- `CLS-PATH-001` joins the standing gate set; a future re-layout requires amending this ADR,
  not just moving files.

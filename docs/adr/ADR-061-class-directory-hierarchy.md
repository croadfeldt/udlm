# UDLM ADR-061: The classes directory mirrors the class hierarchy — a verified projection

**Status:** Proposed (croadfeldt upstream) — **requires engineering ratification**; maintainer decision 2026-08-04
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
│   ├── compute.yaml                  Compute            (base)
│   └── compute/
│       └── vm.yaml                   Compute.VM         (type)
└── process/
    ├── automation.yaml               Automation         (base)
    ├── automation/
    │   ├── ospatch.yaml              Automation.OSPatch (type)
    │   └── ospatch/
    │       ├── engine-blue.yaml      …EngineBlue        (provider)
    │       └── engine-green.yaml     …EngineGreen       (provider)
    └── job.yaml                      Job                (childless base — an
                                                          instantiable base is a file
                                                          with no directory)
```

The rules:

1. **First path component = `lower(family)`.** Family is the grouping axis, not a tier; it
   appears in the path exactly once.
2. **Each dotted segment of `resource_type` is one path component**, the last one the
   filename. Provider tier needs no special case — it is simply the third level.
3. **Filenames are the leaf segment only** (`vm.yaml`, never `compute.vm.yaml`) — the path
   carries the ancestry. Segment casing follows the file-naming standard: word boundaries
   hyphenate (`bare-metal-host`), acronym runs merge with what follows (`ospatch`, `vm`,
   `ipaddress`).
4. **No version directories** (ADR-051 owns versions) and **no tier directories** — tier is
   derivable from depth and declared in the record; naming directories `base/`/`type/` would
   restate it a third time.
5. **The sibling pair is the template** (`compute.yaml` beside `compute/`), not an index file
   (`compute/_base.yaml`): filenames keep the class's own name, no reserved names exist, and a
   class never moves when it gains its first child. `ls classes/process/automation/` is the
   answer to "what does Automation offer."

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

## Consequences

- The bulk conversion lands its ~45 type classes into this shape from birth; family
  directories make the later factoring waves (scope promotion) visible as file moves up a
  level, gated the whole way.
- `CLS-PATH-001` joins the standing gate set; a future re-layout requires amending this ADR,
  not just moving files.

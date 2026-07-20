# ADR-028: Rule-ID naming convention and central registry

**Status:** Accepted (2026-07-18)
**Related:** ADR-026 (`<noun>_type` naming); `registry/rule-id-naming.md`; `registry/rule-id-registry.yaml`; `tests/check_single_source.py`

## Context

Every normative rule in the spec carries a stable ID (`ENT-006`, `PRV-009`, …) so a doc or a
peer can cite one rule and land on one definition. But the prefixes were minted ad hoc, with no
registry of which prefix means what or where it lives. The result was predictable: an inventory
of the 39 normative prefixes found **8 defined across more than one file**, and **4 with genuine
same-number/different-rule collisions** — `ENT-001..005` (entity invariants vs resource/service
entity rules), `INF-001/003/004/006/007` (data-persistence vs information-provider), `GRP-001..005`
(resource-grouping vs universal-groups), and `OBS-002`. `check_single_source.py` existed but
carried its "which prefix lives where" knowledge as a hardcoded baseline, and **was never wired
into CI** — so the drift went unnoticed and unenforced.

## Decision

**Rule-ID prefixes are governed by a naming convention and a central registry; the registry is the
single source of truth; a CI check enforces it.**

1. **Convention** (`registry/rule-id-naming.md`): IDs are `PREFIX-NNN`; `PREFIX` is a unique
   2–6-char mnemonic; **one prefix = one rule family = one home file**; a rule *definition* is an
   ID-first table row and may appear only in the home; IDs are **immutable once published**
   (retire + supersede, never repoint); collisions are resolved by renumbering to a disjoint
   prefix (the `REL-* → ERL-*` precedent), not coexistence.
2. **Registry** (`registry/rule-id-registry.yaml`, validated by `rule-id-registry.schema.json`):
   one record per prefix — `prefix`, `name`, `home`, `domain`, `status`, and optionally
   `baseline_spread` (temporary dedup **debt** to burn down) or `additional_homes` (a
   **sanctioned** permanent co-definition: a family that deliberately spans more than one doc
   with a coordinated number space and no duplicate ID — e.g. `GRP` across resource-grouping and
   the Universal Group Model, which itself asserts "every GRP-* id has exactly one definition").
   The enforced invariant is *one definition per ID*, not literally one file per prefix.
3. **Enforcement** (`tests/check_single_source.py`, now CI-wired): fails on an unregistered prefix,
   a definition outside its home, an ungrandfathered id-collision, or a malformed registry;
   reports a stale baseline so the debt ratchets to zero.

**Data · Policy · Provider:** *Data* — the rule-ID registry is a UDLM artifact (like the standards
and enum registries). *Policy* — n/a (this is authoring/spec hygiene, not a runtime decision).
*Provider* — n/a.

## Consequences

- New rule families must register their prefix before use; drift can't reappear silently.
- The 8 grandfathered spreads (4 real collisions + 4 prefix-spreads) are tracked as explicit debt
  and burned down in a follow-up renumber PR (`ENT` stray rows → `RSE-*`, `INF` persistence rows →
  a new `DSC-*`, fold `GRP`/`OBS`/`AUD`/`OPS`/`REL`/`STO`), after which `baseline_spread` empties
  and the check is fully strict.
- Reuses UDLM's existing registry pattern (standards-adoption-register, the canonical enum
  registry, the ADR index) rather than inventing new machinery.

## Alternatives considered

- **Keep the hardcoded baseline in the check** — rejected: the "which prefix lives where" knowledge
  belongs in a registry humans and tools can read, not buried in a script; and it wasn't wired in.
- **Markdown register** instead of schema-validated YAML — rejected: inconsistent with UDLM's
  valid-by-construction registries; a generated Markdown view can be added later if desired.
- **Allow prefix coexistence across files** (namespacing by file) — rejected: it re-opens the exact
  ambiguity the IDs exist to prevent.

# UDLM ADR-039: Reference vocabularies as staged, cleaned, provenance-tracked Data (vocabulary ingest — Data leg)

**Number:** ADR-039 (the vocabulary-ingest Data leg; an application of ADR-037/PVD).
**Status:** Proposed  **Date:** 2026-07-21
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)
**Related:** ADR-012 (data-references **and** lineage — the cleaning primitive); the curation lifecycle
`proposed → under-review → canonical → deprecated` (`foundations/four-states.md`); ADR-004 (capability
declaration); ADR-029 (inventory / discovery-sourced types); PVD-001 (the reference discipline — the
machine-readable reference graph this consumes); provenance `source_type` (context-and-purpose §4.4)

## Context
PVD-001 turned selectable values into references to Knowledge / reference-data vocabularies (`guest_os` →
`os_image`, `storage_class` → Platform.StorageClass). That **relocates** toil — from typing a string inline to
maintaining a vocabulary — and is net-negative unless populating those vocabularies is both **low-toil** and
**safe**. The real workflows are bulk, not one-at-a-time: *mass-import then clean*, or *consolidate-and-clean
outside, then inject*; and **greening a brownfield estate is simply mass-first-use** — a bulk trigger into the
same pipeline. For any of that to be safe, the substrate must supply the **Data** underneath: a place to stage
dirty input, a way to clean it that is auditable, a way to tell cleaned-outside from discovered from first-use,
and the machine-readable statement of *which* vocabularies a type even needs. This ADR settles that Data leg.
The DCM methods (schema-derived injection surface, add-on-use, bulk import / clean / promote) and the
profile-gated governance build on top of it and are **out of scope here** (their own ADR / profiles).

## Decision
The capability needs **no new types or primitives** — it assembles mechanisms UDLM already has.

1. **Staging *is* the curation lifecycle.** A vocabulary value enters as **`proposed`** — a dirty-safe holding
   pen where sprawl is allowed and cheap. **`canonical`** is the promoted, portable set. Reference resolution
   honors the `proposed`/`canonical` distinction so consumers can require canonical vocabulary. *No dedicated
   "staging" or "import" type* (T7).

2. **Cleaning *is* lineage (ADR-012).** Dedupe = **supersede many → one**; normalize / rename = **supersede-
   with-rename**; consolidation is a sequence of lineage ops, **not deletion** — every merge is an auditable,
   record-level, reversible act. *No dedicated "cleaning" primitive* (T7).

3. **Provenance discriminates the source.** `source_type: import | discovery | provider | consumer` records how
   each value arrived — cleaned-outside-then-injected (`import`), provider-discovered (`discovery`/`provider`),
   or added on first use (`consumer`) — set at ingest and carried through promotion. This is what lets policy
   and the runbook treat the two operational paths differently.

4. **The reference graph is the requirement source.** A resource type's PVD-001 reference markers are the
   machine-readable declaration of which vocabularies it depends on — the input DCM reflects to build the
   injection surface and to know what a given type needs populated. UDLM's job is only to *carry* that graph
   declaratively; walking it is DCM.

5. **Add-on-first-use mints `proposed`, never `canonical`.** A referenced value not yet in the vocabulary is
   offered to it as `proposed`; promotion to `canonical` is a separate, governed (profile) act. Mass-import and
   brownfield greening land at the same front door (`proposed`, at scale). **This is the load-bearing guardrail:
   it is what keeps tag-on-use from minting `rhel-9` / `rhel9` / `RHEL9.0` as three canonical values and
   quietly undoing the portability PVD-001 bought.** Import is frictionless; canonicalization is deliberate.

## Data · Policy · Provider (SPEC-DESIGN §29)
- **Data** — the vocabulary records, their curation states (the staging/promote gate), provenance, and lineage
  (the cleaning trail). All declarative; this ADR is entirely within the Data domain.
- **Policy** — DCM promotes `proposed → canonical` under profile governance; the gate itself is Policy, not Data.
- **Provider** — optional discovery adapters feed the same `proposed` front door; they are not privileged over
  UI/CSV/API import.

## Options considered
- **(A) A dedicated staging/import type + a cleaning/merge primitive.** Rejected — the curation states already
  give a dirty-safe stage and `canonical` gate, and ADR-012 lineage already expresses dedupe/normalize as
  supersession. Coining either is a T7 finding.
- **(B) Add-on-use writes `canonical` directly.** Rejected — that is the Jira label-sprawl failure mode, and it
  re-opens the exact portability hole PVD-001 closed. Sprawl belongs in `proposed`, behind a promotion gate.
- **(C) [chosen]** Curation-states-as-staging + lineage-as-cleaning + provenance-discriminates-source + governed
  promotion, driven by the PVD-001 reference graph.

## Consequences
- DCM builds the injection surface (UI/CSV/API), add-on-use hook, and bulk import/clean/promote **on this model**
  — nothing in those methods needs new substrate.
- Profiles gate promotion (`dev` auto-promote → `sovereign` dual-approval); expand-from-declaration is likewise
  profile-gated — both consume, don't extend, this Data.
- The best-practices runbook's spine is a direct corollary: **"import freely (`proposed`), promote deliberately
  (`canonical`)."**
- Both operational paths converge here: *clean-inside* is lineage ops over `proposed`; *clean-outside-then-
  inject* lands `import`-provenance `proposed` (or trusted `canonical` by profile). One data model, two
  workflows — the reason the capability doesn't fork.

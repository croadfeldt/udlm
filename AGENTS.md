# AGENTS.md — UDLM

> Cross-agent context file ([agents.md](https://agents.md) standard). `CLAUDE.md` is a symlink to this
> file so Claude Code reads the same source of truth. Keep this current as the spec evolves.

## What this repo is

**UDLM — the Unified Data-center Lifecycle Model.** A vendor-neutral, **Apache-2.0**, **pre-1.0
(`udlm/0.1`)** specification: the data model for declaring data-center resources (intent), realizing
them, discovering them, and rebuilding them. It is *spec and schema only* — no runtime/controller lives
here (DCM realizes the model; see the isolation table below).

## Layout

```
foundations/      The four states (Intent→Requested→Realized→Discovered), entity UUID, rehydration, drift
registry/         Resource-type registry + the meta-schema + the definition RULES + common elements
  SPEC-DESIGN-REQUIREMENTS.md   ← THE rules every type/element MUST follow (read this first)
  resource-type-spec.schema.json ← the type-definition meta-schema
  common-elements.md             ← canonical shared shapes (Quantity, ComputeResources, Identity, …)
  resource-type-data-sources.md  ← which industry standard each type adopts, + license verdicts
entities/         Cross-cutting entity concerns (service-dependencies, composition_visibility, …)
design-principles/  Adopted-standards disposition (absorb/embed/adopt), provenance & licensing
lifecycle/        Operational models, recovery state machine
```

## Operating rules (non-negotiable)

- **Commits:** `--no-gpg-sign`, author = the repo owner's public git identity (match `git log -1 --format='%an <%ae>'`), trailer
  `Co-Authored-By: <the Claude model in use> <noreply@anthropic.com>`. This repo is on **GitHub**
  (`cexample/udlm`) — use `gh`, not `glab`.
- **PRs are subject-scoped** — one logical thing per PR, ≤2–3k lines.
- **Run `bash scripts/signoff.sh` before every PR** — all hard gates (registry, meta-schema,
  estate tokens, single-source, vocabulary, profile tables, compat vs origin/main) + the judgment
  checklist. The cleanliness bar and sweep process live in the dav repo:
  `docs/repo-cleanliness-review.md` (the twelve questions) + `docs/runbook-overnight-sweep.md`.
- **Audience: human engineers. Voice: software and data-model architect** — declarative,
  model-grounded, references carry their gist, no editorializing.
- **The definition rules are law.** Every new resource type or common element MUST satisfy
  `registry/SPEC-DESIGN-REQUIREMENTS.md`. The load-bearing ones:
  - **No vendor-exclusive data in the portable spec** (§17, §24). Provider-specific data is a
    **Provider-Class `SharedDataElement`** (ADR-038); the old `provider_extensions`/`provider_hints`
    carriers are removed — the validator rejects them (schema realization tracked in #199).
  - **Reuse canonical common-elements** (§24–25) — **snake_case** (settled 2026-06-27; never re-litigate), explicit-unit `Quantity`, RFC 3339.
  - **Adopt standards by reference, record provenance + license** (§22–23): every `adopts[]` entry
    carries `source` (name/version/URL) and `license` + `license_compatibility`
    (`compatible-vendor` | `compatible-reference` | `reference-only`). UDLM is Apache-2.0 — copying
    schema text only from Apache-compatible sources; copyleft (GPL/MPL) is **reference-by-name only**.
  - **Component granularity is both-ways** (§26): the parent always carries the **rollup** data element
    (`memory.size`); a component MAY *also* be a first-class `Hardware.*` entity `contained_by` it,
    toggled by `composition_visibility`. Rollup = reconciled aggregate; mismatch = drift.
  - **Same-type instances must be distinguishable** (§27): every component carries the canonical
    `Identity` (`location` → `serial_number`/`wwn` → `role`) so two identical DIMMs / two same-use
    drives are individually addressable.
  - **Raw resources are first-class** (§28): a type MUST be instantiable with Discovered state and **no
    Intent** (racked-but-unallocated, brownfield), carrying `lifecycle_state: available`, later
    **adopted** (Intent attached, UUID preserved).
- **Adding a type:** follow `registry/naming-conventions.md` (Tier-1 `Category.Type` vendor-neutral,
  name-to-a-standard-first) and the registry process (`governance/registry-governance.md` §3,
  `CONTRIBUTING.md`): define it in `registry/` validating against `resource-type-spec.schema.json`; fill
  `adopts[]` with source+license; reuse common-elements; ship ≥1 worked example; never inline
  vendor-exclusive fields. The standard each type adopts is tabulated in
  `registry/resource-type-data-sources.md`.

## Isolation (where things live)

| Concern | Repo |
|---|---|
| **Spec + resource-type registry** (the *types*) | `udlm` (this repo, cexample/udlm) |
| **DCM** control-plane / consumer code | `dcm` (cexample/dcm) |
| **DAV** review console | `dav` (cexample/dav) |
| **Estate DATA** (instances, the dependency graph) | a private estate-data repo (kept off GitHub — no personal infrastructure in the public specs) |

## Current state (2026-07-25)

**0.1 surface is complete** (the September release is **0.1**; 1.0 is only the earned milestone —
never conflate them). All ADRs and DecisionRecords are **Proposed**: ratification sits with the
engineering team (issue #217) — never claim Accepted/ratified status.

**Settled this cycle (write to this reality):**
- **Edge model:** `edge_type` (`depends_on`|`contained_by`|`binds_to`|`references`) + `strength`
  (hard|soft) + declared `relation`; nature is derived; the Atomic/Composite **shape is derived**
  (`has_constituents`), never stored (ADR-027 addendum); `kind`/`dependency_type`/
  `relationship_type` are retired and guarded (tests/check_model_vocabulary.py, incl. prose).
- **`provider_extensions` is removed** (ADR-038 subsumption executed; validator rejects it).
- **provider-contract.md owns the whole provider/capability surface**: registration §2, sovereignty
  obligations `SOV-*` §2a, capability profiles §8, registry §9, discovery wire protocol §10
  (capability-discovery.md is a stub — never cite it as a home).
- **Six profiles:** homelab → dev → standard → prod → fsi → sovereign (`docs/profiles.md`;
  `minimal` is retired).
- **Audit is Merkle** (RFC 9162): events are `audit.integrity_alert`/`audit.integrity_break`;
  linear hash-chain wording is a defect.
- **Core tenet T9:** the substrate never translates into a provider's native spec.
- **ADR-029 Hardware ancillary types landed** (StorageDevice / Processor / GraphicsProcessor 0.2.0)
  — the roadfeldt estate validates 288+ records / 0 failures against main.

**In flight:** engineering ratification pass (#217); the dcm-project downstream publishing wave
(UC-priority split per the Jordi criteria — 21-UC-required PRs first); `SharedDataElement` schema
realization (#199); Ansible estate discovery feeding Discovered state (croadfeldt/dcm#79).

**Navigation:** `docs/file-index.md` (ownership per file) · `registry/UDLM-0.1-SCOPE.md` (the 21
UCs + tag gate) · `docs/adr/README.md` (decision index) · `CONTRIBUTING.md` (the checklist).

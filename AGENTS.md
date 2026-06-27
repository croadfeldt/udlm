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

- **Commits:** `--no-gpg-sign`, author `Maintainer example <maintainer@example.com>`, trailer
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. This repo is on **GitHub**
  (`cexample/udlm`) — use `gh`, not `glab`.
- **PRs are subject-scoped** — one logical thing per PR (see open PRs below).
- **The definition rules are law.** Every new resource type or common element MUST satisfy
  `registry/SPEC-DESIGN-REQUIREMENTS.md`. The load-bearing ones:
  - **No vendor-exclusive data in the portable spec** (§17, §24). Vendor specifics live only at the
    extension surface (`portability: provider-specific` / `provider_hints`).
  - **Reuse canonical common-elements** (§24–25) — camelCase, explicit-unit `Quantity`, RFC 3339.
  - **Adopt standards by reference, record provenance + license** (§22–23): every `adopts[]` entry
    carries `source` (name/version/URL) and `license` + `licenseCompatibility`
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
| **Homelab estate DATA** (instances, the dependency graph) | `estate-repo` (a private repo) |

## Current state (2026-06-26)

Open PRs (stacked): **#1** Resource Type Registry + cross-cutting principles · **#2** DecisionRecord
Knowledge entity (stacked on #1) · **#3** adopted-standard provenance/license rules + data-source matrix
+ cross-type consistency + component model (this branch, `feat/resource-type-data-sources`).

**Recently added to the spec (this thread):**
- Provenance + license rules for adopted standards (SPEC-DESIGN §22–23; `design-principles/adopted-standards.md`).
- Cross-type consistency rules + `registry/common-elements.md` (canonical Quantity / ComputeResources /
  cidr / ip_family / Reference / Condition + the sweep finding: the 4 existing types express cpu/memory
  three ways → normalize additively, converge at next MAJOR).
- Component granularity §26 + `common-elements.md` §5 (entity vs data element, both ways; `Hardware.*` family).
- Instance identity §27 + `common-elements.md` §5a (`Identity` discriminators).
- Raw/unallocated resources §28 + `four-states.md` §2.4 + `common-elements.md` §6 (`lifecycle_state`).

**Pending:** author the `Hardware.*` component types (MemoryModule, StorageDevice, NetworkInterface,
GraphicsProcessor, Processor) and the 8 infra types (BareMetalInstance, CephCluster, Gateway,
AddressService, DirectoryService, PowerFeed, …) against these rules; verify the two `verify` licenses
(OSAC, heatmiser) in the data-source matrix.

# UDLM ADR-015: Settings and Configuration Bundles

**Status:** Proposed (2026-07-15)
**Type:** Architecture Decision Record (a `DecisionRecord` with architecture scope — `entities/knowledge-family.md` §4.5)
**Related:** ADR-008 (UDLM/DCM boundary — "could a peer differ? yes → DCM"); ADR-007 (profiles are composed *sets*, not levels); ADR-014 (optionality with conformity — data provides transport + conformity, provider/org owns the requirement); `foundations/layering-and-versioning.md` (the layer/assembly/precedence model this reuses).

## Context

Settings — profile-governed values, thresholds, toggles — were scattered across docs and **restated wherever a doc branched on them**, and they drifted (A5: the interaction-credential lifetime was defined two different ways). The single-source guard catches a duplicate **rule-ID**, but a duplicate **value table** has no ID, so this class kept recurring.

The deeper issue: a "setting" is not just a value. From the **data model** it is a *parameter + allowed values + rule*. But **operating** it pulls in configuration, usability, enforcement, and enablement — realization concerns. And in practice settings want to be **grouped and composed** (base defaults, per-module settings, profile overlays, org/tenant overrides), not managed one scattered value at a time. UDLM needs one model for *defining* settings and one for *managing* them, on the right side of the UDLM/DCM boundary.

## Decision

### 1. A Setting is a UDLM data primitive

A **Setting** is a named parameter with a typed value and a rule:

```yaml
setting:
  name: credential.max_lifetime          # stable id, one home
  value_type: duration                   # duration | enum | number | boolean | string | ref
  constraint: ">= PT5M"                   # the rule (allowed values / bounds / enum)
  scope: platform | tenant | resource | domain
  conformity: comparable                 # does the value mean the same across peers? (ADR-014)
  profile_governed: true                 # does it vary by profile?
  default: PT1H                           # or a per-profile default set (below)
```

UDLM owns the **definition** — the parameter, its legal values, and the rule — and *nothing about how it is applied*. This is the ADR-014 split: the data carries transport + conformity; the concrete requirement/choice is provider/org/realization.

### 2. Settings compose in Configuration Bundles — the layer model, applied to config

Settings are grouped into **configuration bundles**, composed in **precedence order**. This is not a new mechanism — it is `layering-and-versioning.md`'s layer/assembly model applied to settings:

| Bundle | What it holds | Precedence |
|--------|---------------|-----------|
| **base** | substrate defaults — the floor | lowest |
| **module** | a capability/subsystem's settings (`credentials`, `versioning`, `sovereignty`, …) | over base |
| **profile** | the profile overlay — a profile **is** a composed set of settings (ADR-007), `minimal`…`sovereign` | over module |
| **org / tenant / domain** | overlays that **tighten** (never weaken a security floor) | highest |

Composition is deterministic precedence (`base < module < profile < org < tenant`), producing an **effective configuration** for a context — exactly as layer assembly produces effective field values, with the same provenance (which bundle set which value). A bundle is a **versioned, coherent, manageable unit** — the "bundles of config, grouped and manageable" this ADR is named for. A profile-governed setting carries a per-profile default *set* inside the profile bundle (the `credentials.md §12.1` `max_lifetime` block is the model instance).

### 3. UDLM defines; DCM manages — the four faces of a setting

UDLM's job ends at the setting's **definition** + the **bundle structure** + the **composition rule**. Operating a setting is **DCM's**, across four faces:

| Face | Whose | What it is |
|------|-------|-----------|
| **Definition** | **UDLM (Data)** | the parameter, values, rule, conformity, profile-governance, defaults |
| **Configuration** | **DCM** | how a value is set + the override precedence that resolves the *effective* value from the bundles |
| **Usability** | **DCM** | how the setting is projected to a user — the config interface (`provider-contract.md §1a.3` config-projection) |
| **Enforcement** | **DCM** | where/how the effective value is applied — the boundary/gate that reads it |
| **Enablement** | **DCM** | whether the setting is active/admitted — default-deny-style availability, feature gating |

UDLM supplies the **data primitives** DCM's four faces rest on — a setting declares its `scope`, precedence-eligibility, an enforcement-point reference, and an enablement gate — but a peer MAY implement configuration, usability, enforcement, and enablement **differently and still be conformant** (ADR-008: could a peer differ? yes → DCM). What a peer may **not** differ on is the definition + the composition contract (or the effective value diverges and portability breaks).

### 4. Single-source — and now enforced for value tables too

Each setting is **defined once**, in its owning bundle/module doc; the effective value is **composed**, never restated. Two enforcement aids, mirroring the file-index + single-source guard:

- **A profile-settings index** (`registry/profile-settings-index.md`) — every profile-governed setting → its owning bundle/doc/block. The knobs are visible in one place (the file-index, for settings).
- **A guard extension** (`tests/check_single_source.py`) — a **profile-column value table** (`minimal … sovereign`) that appears for the same setting in more than one doc is flagged, the way a duplicate rule-ID is. This closes the exact gap that hid A5 (a duplicated table has no ID for the original guard to catch).

## Rule of thumb

> **Define the setting once (UDLM); compose it in a bundle; let DCM configure, surface, enforce, and enable it.** A per-profile value table lives in exactly one bundle — everywhere else references it.

## Data · Policy · Provider (required lens — SPEC-DESIGN §29)
- **Data (UDLM):** the setting definition, the bundle structure, the composition/precedence rule.
- **Policy (DCM/org):** which optional settings are *required* in a context; the org/tenant overlay bundles.
- **Provider:** declares which settings it honors and their supported values (like `adopted_standard_support`).

## Options considered
- **Status quo — settings per doc, restated** — rejected: it is the drift this fixes (A5).
- **A flat global settings registry** — rejected: settings are naturally grouped (module, profile) and composed; a flat list loses the bundle structure and the precedence semantics teams actually manage by.
- **Config bundles over the existing layer model + UDLM/DCM four-face split** — **chosen.** Reuses layering, formalizes profiles as one bundle kind, and puts each concern on the right side of the boundary.

## Consequences
- Settings stop drifting: one definition, composed bundles, a guard that now sees value tables.
- Profiles are formally **one bundle kind** — aligns and reuses ADR-007 (composed sets).
- No new composition machinery — it is the layer/assembly model.
- DCM gets a clear **four-face** contract for settings management resting on UDLM primitives.
- **Migration:** existing scattered profile tables collapse to their owning bundle + a reference. The dedup PRs already began this; **A5 is the worked case** (the accreditation-matrix table now references `credentials.md §12.1`).

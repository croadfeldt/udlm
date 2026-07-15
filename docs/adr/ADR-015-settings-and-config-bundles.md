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
  scope: tenant                           # OVERRIDE CEILING — the finest tier on the scope ladder (§2a)
                                          #   at which this may be set; settable base…tenant, an override
                                          #   at any finer tier is REJECTED. `platform` = ceiling `profile`.
  override_direction: tighten_only        # free | tighten_only — a finer layer may only NARROW the value
                                          #   per the comparator (a security floor is tighten_only), never weaken it
  conformity: comparable                 # does the value mean the same across peers? (ADR-014)
  profile_governed: true                 # does it vary by profile?
  default: PT1H                           # or a per-profile default set (below)
```

UDLM owns the **definition** — the parameter, its legal values, and the rule — and *nothing about how it is applied*. This is the ADR-014 split: the data carries transport + conformity; the concrete requirement/choice is provider/org/realization.

### 2. Settings compose in Configuration Bundles — the layer model, applied to config

Settings are grouped into **configuration bundles**, composed in **precedence order**. This is not a new mechanism — it is `layering-and-versioning.md`'s layer/assembly model applied to settings:

| Bundle (tier) | What it holds | Scope value it declares | Precedence |
|--------|---------------|---------|-----------|
| **base** | substrate defaults — the floor | — (platform singleton) | lowest |
| **module** | a capability/subsystem's settings (`credentials`, `versioning`, `sovereignty`, …) | the module id | over base |
| **profile** | the profile overlay — a profile **is** a composed set of settings (ADR-007), `dev`…`sovereign` | the profile id | over module |
| **org** | organization-wide overlay | the org id | over profile |
| **domain** | compliance-domain overlay (`fsi`, …) | the domain id | over org |
| **tenant** | per-tenant overlay | the tenant uuid | over domain |
| **resource** | per-resource overlay | the resource uuid | highest |

Composition is deterministic precedence along the **one canonical scope ladder** (`base ▸ module ▸ profile ▸ org ▸ domain ▸ tenant ▸ resource`), producing an **effective configuration** for a context — exactly as layer assembly produces effective field values, with the same provenance (which bundle set which value). Overlays **tighten**, never weaken a security floor (enforced per-setting by `override_direction`, §2a). A bundle is a **versioned, coherent, manageable unit** — the "bundles of config, grouped and manageable" this ADR is named for. A profile-governed setting carries a per-profile default *set* inside the profile bundle (the `credentials.md §12.1` `max_lifetime` block is the model instance).

### 2a. Scoping — the two declarations that make precedence *resolvable*

Precedence *orders* layers; to actually **resolve** a setting the resolver must also know **how far down a setting may be set** and **which overlay is in scope for this request**. Two declarations supply that, both against the one ladder above — so `Setting.scope`, the bundle tiers, and `profile-resolution.md §1`'s precedence are finally **one vocabulary**, not three.

**(1) A setting declares its override ceiling** (§1). `scope` is the **finest tier at which the setting may be set**: settable from `base` up to and including `scope`, an override at any finer tier is **rejected** (never silently dropped). `scope: platform` is shorthand for ceiling `profile` — platform-wide, no org/tenant/resource override. `override_direction: free | tighten_only` adds the *direction*: a `tighten_only` floor may only be **narrowed** by a finer layer, per the value's comparator (`duration` → shorter; numeric → the tightening bound; `enum` → a declared sub-order), never weakened. Together these are the setting's **precedence-eligibility** (named in §3).

**(2) An overlay bundle declares its scoping value.** A bundle is `(tier, scope_value)` — its tier on the ladder **and which instance of that tier it binds to**. `base` and `profile` are platform singletons; `module`, `org`, `domain`, `tenant`, `resource` each carry the **selector** that says *which* one this overlay is:

```yaml
config_bundle:
  tier: tenant
  scope_value: <tenant-uuid>            # THIS tenant — how the resolver knows the overlay applies
  settings:
    credential.max_lifetime: PT15M
```

Without `scope_value` the resolver can order tiers but cannot select which tenant/module/domain overlay applies. A set value is therefore `{ setting, tier, scope_value, value }` — enough to stack by precedence and record provenance.

**Resolution, for a request in a context** (its coordinates: profile, org, domain, tenant, resource — and the module each setting belongs to):
1. **Select** every bundle whose `(tier, scope_value)` matches a context coordinate, plus the platform `base`/`profile` singletons.
2. **Order** the selected bundles by ladder tier.
3. **Compose** per setting: take the value from the highest-tier selected bundle that is **≤ the setting's ceiling**; reject any value set above the ceiling; if the setting is `tighten_only`, reject a finer value that weakens the coarser one.
4. The result is the **effective value** + its provenance (the winning `(tier, scope_value)`).

That is what makes precedence *effective* rather than merely ordered: the setting says how far down it may be pushed and in which direction; each overlay says which slice of the estate it is; the resolver matches, orders, and composes.

**Authorization is Policy / RBAC's, not the settings data model's.** The declarations above make an override *addressable and bounded* — a change targets a `(tier, scope_value)` and is bounded by the setting's ceiling + direction. **Who is permitted to write an overlay at a given `(tier, scope_value)` — who may set a tenant value, who may tighten a domain floor, who may touch the platform base — is a Policy / RBAC decision** (`RBAC-001`, `contracts/policy-contract.md`), enforced by DCM at set time, not encoded in the setting or the bundle. This is the ADR-008 boundary: a peer MAY authorize the *who* differently and stay conformant; what it may not differ on is the coordinates and the composition contract. The data model bounds *what and where*; RBAC governs *who*.

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
- **Policy (DCM/org):** which optional settings are *required* in a context; the org/tenant overlay bundles; and **RBAC governs *who* may write an overlay at a given `(tier, scope_value)`** (`RBAC-001`) — the data model bounds *what/where*, policy authorizes *who* (§2a).
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

# UDLM ADR-015: Settings and Configuration Bundles

**Status:** Accepted (2026-07-15)
**Realized by:** `registry/layer.schema.json` (`extends`, `limits`) · `docs/spec/foundations/layering-and-versioning.md` `LAY-009`/`LAY-010` · `tests/check_layer_limits.py`
**Type:** Architecture Decision Record (a `DecisionRecord` with architecture scope — `docs/spec/foundations/knowledge-family.md` §4.5)
**Background — read first (the cold reader's on-ramp; skip if you have the context).** ADR-008 (the substrate and its control plane boundary — "could a peer differ? yes → the control plane"); ADR-007 (profiles are composed *sets*, not levels); DCM ADR-014 (optionality with conformity — data provides transport + conformity, provider/org owns the requirement); `docs/spec/foundations/layering-and-versioning.md` (the layer/assembly/precedence model this reuses).

## Context

Settings — profile-governed values, thresholds, toggles — were scattered across docs and **restated wherever a doc branched on them**, and they drifted (A5: the interaction-credential lifetime was defined two different ways). The single-source guard catches a duplicate **rule-ID**, but a duplicate **value table** has no ID, so this class kept recurring.

The deeper issue: a "setting" is not just a value. From the **data model** it is a *parameter + allowed values + rule*. But **operating** it pulls in configuration, usability, enforcement, and enablement — implementation concerns. And in practice settings want to be **grouped and composed** (base defaults, per-module settings, profile overlays, org/tenant overrides), not managed one scattered value at a time. UDLM needs one model for *defining* settings and one for *managing* them, on the right side of the substrate/implementation boundary.

## Decision

### 1. A Setting is a layer field — not a primitive of its own

A setting is a **named value with a rule about who may change it and how far**. That is a layer
field, exactly: a layer contributes values, declares the envelope its descendants must stay inside
(`limits`, `LAY-009`), and states who it applies to (`covers`). Nothing about a setting needs a
second mechanism.

```yaml
# The setting AND its ceiling, on one layer. `limits` is the override rule: a descendant may
# narrow within the envelope and cannot leave it, and there is no override for a bound —
# declining the layer via `skip` is the audited route, visible as a skip.
record_type: layer
handle: core/credential-floor
precedence_class: core                    # WHERE in the merge order
domain: platform                          # WHOSE authority sets it
covers: estate?resource_type==Access.*    # WHO it applies to
limits:
  credential.max_lifetime:
    - min: PT5M
      max: PT1H
      reason: The org's credential floor; a finer layer may narrow, never widen.
fields:
  credential.max_lifetime: PT1H
```

**Why not a primitive.** Every part the original shape asked for now exists, and each is stronger
in its layer form:

| The setting shape wanted | The layer already has | And it is better because |
|---|---|---|
| `scope` — an override ceiling | `limits` | a ceiling states the BOUND, where a tier states only how far down someone may write. A tier cannot say `PT5M..PT1H`. |
| `override_direction: tighten_only` | `limits` | a direction can only be judged against whatever happened to merge beneath it; an envelope is checkable against every descendant independently, which is what makes one validation pass work over a deep chain. |
| the §3 scoping filter | `covers` / `from_layers` / `skip` | already the two-sided handshake, already governed for skipping. |
| effective value + provenance | `LAY-005` / `LAY-008` | already compute-never-store, already per-field. |

`value_type`, `constraint`, `conformity` and `default` are the element's own `schema` and
`SharedDataElement` concerns — the layer carries the value, the class carries what a valid value is.

**The one thing that was genuinely missing** was the envelope, and it now exists (`LAY-009`). That is
why this decision reduces rather than builds: the mechanism arrived by another route.

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

Precedence *orders* layers; to actually **resolve** a setting the resolver must also know **how far a
value may be moved** and **which overlay is in scope for this request**. Both are declarations on the
layer: `limits` bounds the first, `covers`/`from_layers`/`skip` selects the second.

**There is no single ladder, and asking for one was the error.** This ADR proposed
`base ▸ module ▸ profile ▸ org ▸ domain ▸ tenant ▸ resource` as the one vocabulary that would
replace three. It could not be built, because it fuses **two independent axes** into one line:

| Axis | Answers | Carried by |
|---|---|---|
| **precedence** | WHERE in the merge order — who overrides whom | `precedence_class` (`base ▸ core ▸ intermediate ▸ service ▸ request ▸ policy`) |
| **domain** | WHOSE authority sets it | `domain` (`system ▸ platform ▸ tenant ▸ resource_type ▸ entity`) |

They vary independently, and the shipped corpus proves it: `base` appears at both `platform` and
`resource_type` authority; `intermediate` at both `platform` and `tenant`. A flattened seven-tier
line cannot express `base`-order-with-`tenant`-authority at all, so unifying them would have lost
information rather than removed duplication.

The three vocabularies this ADR set out to merge were therefore not three spellings of one thing.
Two of them are the two real axes, and the model already carries both, on every layer.

**(1) A setting declares its override ceiling** (§1). `scope` is the **finest tier at which the setting may be set**: settable from `base` up to and including `scope`, an override at any finer tier is **rejected** (never silently dropped). `scope: platform` is shorthand for ceiling `profile` — platform-wide, no org/tenant/resource override. `override_direction: free | tighten_only` adds the *direction*: a `tighten_only` floor may only be **narrowed** by a finer layer, per the value's comparator (`duration` → shorter; numeric → the tightening bound; `enum` → a declared sub-order), never weakened. Together these are the setting's **precedence-eligibility** (named in §3).

**(2) An overlay bundle declares a scoping filter.** A bundle's `scope` is a **Kubernetes label selector** (adopted CANONICAL — `standards-adoption-register.md` "Kubernetes vocabularies") over the request's **scope coordinates treated as labels** (`profile`, `org`, `domain`, `tenant`, `resource`, `module`): `matchLabels` (equality, AND-ed) + `matchExpressions` with `In | NotIn | Exists | DoesNotExist`, plus an **`except`** list of sub-selectors for compound carve-outs — the Kubernetes **NetworkPolicy `ipBlock.except`** pattern. It is **declarative** by construction, never an expression language (SPEC-DESIGN declarative-constraints tenet). Singletons (`base`, `profile`) need no filter; the general case:

```yaml
config_bundle:
  scope:                                              # a scoping filter over coordinate labels
    matchExpressions:
      - { key: domain, operator: In, values: [x, y, z] }   # applies across a set…
    except:
      - matchLabels: { domain: z, id: "1" }                # …but NOT this (z,1) tuple (invert)
  settings:
    provider.credentials: { ... }
```

A bundle **applies to a request iff** its coordinates satisfy the selector (all `matchLabels`/`matchExpressions` AND-ed) **and match none of the `except` sub-selectors**. One filter covers all four shapes: a single coordinate (`matchLabels: {tenant: X}`), a compound AND (`{tenant: X, domain: Y}`), a set (`domain In [x,y,z]`), and an exclusion/tuple carve-out (`except`). A bundle's **precedence tier is the finest coordinate its filter constrains** (a `{tenant, domain}` tuple ranks at `tenant`), so multi-scoped overlays still compose deterministically on the one ladder. A set value is `{ setting, scope (the filter), value }`.

Without a filter the resolver can order tiers but cannot select which overlay applies; the filter is what makes multi- and exclusion-scoping expressible without a bespoke syntax.

**Resolution, for a request in a context** (its coordinate labels: profile, org, domain, tenant, resource — and the module each setting belongs to):
1. **Select** every bundle whose scoping filter the request's coordinates **satisfy** (matchLabels/matchExpressions AND-ed, and no `except` sub-selector matches), plus the platform `base`/`profile` singletons.
2. **Order** the selected bundles by their precedence tier (the finest coordinate each filter constrains) on the ladder.
3. **Compose** per setting: take the value from the highest-tier selected bundle that is **≤ the setting's ceiling**; reject any value set above the ceiling; if the setting is `tighten_only`, reject a finer value that weakens the coarser one.
4. The result is the **effective value** + its provenance (the winning bundle's filter).

Step 2 orders *tiers*; ordering **within** one tier is ADR-047 — same-tier composition follows explicit `precedence_order` (the `layer.schema.json` primitive), and two same-tier bundles setting the same setting with no declared order are a typed, refused conflict naming both sources.

That is what makes precedence *effective* rather than merely ordered: the setting says how far down it may be pushed and in which direction; each overlay says which slice of the estate it is; the resolver matches, orders, and composes.

**Authorization is Policy / RBAC's, not the settings data model's.** The declarations above make an override *addressable and bounded* — a change targets a `scope` (the filter's coordinates) and is bounded by the setting's ceiling + direction. **Who is permitted to write an overlay at a given scope — who may set a tenant value, who may tighten a domain floor, who may touch the platform base — is a Policy / RBAC decision** (`RBAC-001`, `docs/spec/contracts/policy-contract.md`), enforced by the control plane at set time, not encoded in the setting or the bundle. This is the ADR-008 boundary: a peer MAY authorize the *who* differently and stay conformant; what it may not differ on is the coordinates and the composition contract. The data model bounds *what and where*; RBAC governs *who*.

### 3. UDLM defines; the control plane manages — the four faces of a setting

UDLM's job ends at the setting's **definition** + the **bundle structure** + the **composition rule**. Operating a setting is **the control plane's**, across four faces:

| Face | Whose | What it is |
|------|-------|-----------|
| **Definition** | **UDLM (Data)** | the parameter, values, rule, conformity, profile-governance, defaults |
| **Configuration** | **the control plane** | how a value is set + the override precedence that resolves the *effective* value from the bundles |
| **Usability** | **the control plane** | how the setting is projected to a user — the config interface (`provider-contract.md §1a.3` config-projection) |
| **Enforcement** | **the control plane** | where/how the effective value is applied — the boundary/gate that reads it |
| **Enablement** | **the control plane** | whether the setting is active/admitted — default-deny-style availability, feature gating |

UDLM supplies the **data primitives** the control plane's four faces rest on — a setting declares its `scope`, precedence-eligibility, an enforcement-point reference, and an enablement gate — but a peer MAY implement configuration, usability, enforcement, and enablement **differently and still be conformant** (ADR-008: could a peer differ? yes → the control plane). What a peer may **not** differ on is the definition + the composition contract (or the effective value diverges and portability breaks).

### 4. Single-source — and now enforced for value tables too

Each setting is **defined once**, in its owning bundle/module doc; the effective value is **composed**, never restated. Two enforcement aids, mirroring the file-index + single-source guard:

- **A profile-settings index** (`registry/profile-settings-index.md`) — every profile-governed setting → its owning bundle/doc/block. The knobs are visible in one place (the file-index, for settings).
- **A guard extension** (`tests/check_single_source.py`) — a **profile-column value table** (`homelab … sovereign`) that appears for the same setting in more than one doc is flagged, the way a duplicate rule-ID is. This closes the exact gap that hid A5 (a duplicated table has no ID for the original guard to catch).

## Rule of thumb

> **Define the setting once (UDLM); compose it in a bundle; let the control plane configure, surface, enforce, and enable it.** A per-profile value table lives in exactly one bundle — everywhere else references it.

## Data · Policy · Provider (required lens — SPEC-DESIGN §29)
- **Data (UDLM):** the setting definition, the bundle structure, the composition/precedence rule.
- **Policy (the control plane/org):** which optional settings are *required* in a context; the org/tenant overlay bundles; and **RBAC governs *who* may write an overlay at a given scope** (`RBAC-001`) — the data model bounds *what/where* (the scoping filter), policy authorizes *who* (§2a).
- **Provider:** declares which settings it honors and their supported values (like `adopted_standard_support`).

## Options considered
- **Status quo — settings per doc, restated** — rejected: it is the drift this fixes (A5).
- **A flat global settings registry** — rejected: settings are naturally grouped (module, profile) and composed; a flat list loses the bundle structure and the precedence semantics teams actually manage by.
- **Config bundles over the existing layer model + the substrate and its control plane four-face split** — **chosen.** Reuses layering, formalizes profiles as one bundle kind, and puts each concern on the right side of the boundary.

## Consequences
- Settings stop drifting: one definition, composed bundles, a guard that now sees value tables.
- Profiles are formally **one bundle kind** — aligns and reuses ADR-007 (composed sets).
- No new composition machinery — it is the layer/assembly model.
- the control plane gets a clear **four-face** contract for settings management resting on UDLM primitives.
- **Migration:** existing scattered profile tables collapse to their owning bundle + a reference. The dedup PRs already began this; **A5 is the worked case** (the accreditation-matrix table now references `credentials.md §12.1`).

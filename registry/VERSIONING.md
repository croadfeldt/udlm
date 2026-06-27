# UDLM Registry — Versioning & Compatibility Policy

UDLM versions two things independently. Getting this separation right is what lets the spec
evolve without breaking the registry, and lets a resource type evolve without a spec bump.

## The two axes

| Axis | What it versions | Scheme | Rule |
|---|---|---|---|
| **SPEC** | the UDLM meta-model: this meta-schema, the contracts, four-state lifecycle, identifier scheme | `MAJOR.MINOR` semver | Peers conformant to the same **MAJOR** are wire-compatible (CONFORMANCE.md §9). Cross-major interop = support both majors concurrently. |
| **ENTITY** | each Resource Type Specification | `MAJOR.MINOR.REVISION` | Immutable once published; any change publishes a new version. |

**The binding:** every entity declares `conformsTo: udlm/<spec MAJOR.MINOR>` — its `apiVersion`.
That tells the registry which meta-schema version validates it. Downstream, **constraint
profiles / catalog items (E1)** and **realized instances (E5)** pin the *entity* version they
were built from, so drift is measured against the exact contract that produced them.

## Spec status — pre-1.0 (`udlm/0.1`)

**The UDLM spec is currently `0.1` — a `0.x`, pre-stable release.** The surface is still being
*defined* (registry meta-schema, realized-entity, adopted-standards, the entity-type families), so
per semver §4 anything MAY change and the contract is **not yet considered stable**. Treat the
current work as *expansion of the v0.x surface*, not refinement of a released spec.

**What `1.0` will mean (the earned milestone, not the starting line):** UDLM cuts `1.0` when the
surface is complete, the conformance suite (`CONFORMANCE.md`) passes, and the project is ready to
**commit to backward compatibility** — i.e. when a breaking change would genuinely warrant a `2.0`.
Until then, the SPEC `MAJOR` is `0`, and the "same-MAJOR = wire-compatible" guarantee below is a
*post-1.0* promise; pre-1.0, minor (`0.1 → 0.2`) bumps may carry breaking changes as the surface
settles. This mirrors how FOCUS, OpenTelemetry, and most CNCF specs incubate at `0.x` and earn `1.0`.

## Entity semver — what bumps what

| Change | Bump |
|---|---|
| Add an **optional** field; add an **output**; add a relationship; **widen** validation (looser enum/range) | **MINOR** |
| **Remove/rename** a field; make an existing field **required**; **narrow** validation (tighter enum/range); remove an output/relationship; change `entityType`/`portability`/lifecycle | **MAJOR** |
| Docs, descriptions, metadata, non-semantic edits | **REVISION** |

A **MAJOR** bump is a breaking change: the prior version moves to `deprecated`, and the new
version's `deprecation`-linked predecessor MUST carry `migrationGuidance`. Consumers pinned to
the old major keep working until it is `retired`.

## Deprecation lifecycle (universal model, foundations/layering-and-versioning.md)

```
active ──► deprecated ──► retired
```
- `deprecated` versions still resolve and still serve pinned consumers; they carry
  `deprecation.{date, reason, replacementUuid, migrationGuidance}`.
- **Deprecation window (K8s-informed):** a `deprecated` major is supported for a published
  minimum window before `retired`, so consumers have a real migration runway. Don't retire under
  anyone still pinned without that window.

## Version conversion (K8s-informed)

Multiple entity versions can be live at once. When a consumer pins `vN` but a provider
implements `vM`, conversion is **schema-declared and lossless within a major** (a MINOR adds only
optional/widened fields, so up/down-conversion is mechanical). Cross-major conversion requires an
explicit, declared mapping — never an implicit guess. This mirrors Kubernetes' storage-version +
conversion model: one canonical version per major, declared conversions between the rest.

## Registry resolution

- Reference a type by `resourceType` + a version constraint: exact (`1.2.0`), minor-floating
  (`~1.2`), or major-floating (`^1`). Default resolution returns the latest **active** version
  satisfying the constraint.
- `deprecated` versions resolve only to consumers that pin them; `retired` versions do not resolve.

## Pre-1.0 surface-change log

While the spec is `0.x` the surface is still being **defined**, so changes are *expansion of the v0.x
surface*, not refinement of a released contract (see "Spec status" above).

**Pre-1.0 we do NOT follow the full versioning rules above.** Those rules (immutable-once-published,
MAJOR for breaking changes + deprecation window) are the *post-1.0* discipline that protects consumers
pinned to a released contract — which don't exist yet. While `0.x`:

- Versions still **advance** (we bump the REVISION) so a reader can tell a definition changed, **but a
  `0.x` REVISION/MINOR MAY carry backward-incompatible (breaking) changes** that post-1.0 would require
  a MAJOR + deprecation. No deprecation ceremony is performed pre-1.0.
- Every such change is **logged here** so the breakage is explicit, not silent.

| Date | Version | Change | Breaking? | Migration |
|---|---|---|---|---|
| 2026-06-26 | `Data.Database` & `Compute.Cluster` → **0.1.1**; meta-schema (SPEC `udlm/0.1`) edited in place | `adoptedStandardRef` (`resource-type-spec.schema.json`) now requires `source`, `license`, `licenseCompatibility`; `identityJoin` relaxed to optional (SPEC-DESIGN-REQUIREMENTS §22–23). | **Yes — backward-incompatible.** An `adopts[]` entry without the license verdict no longer validates (would be a MAJOR post-1.0; carried in a `0.1.1` REVISION by the pre-1.0 exception above). **Wire/instance format is unaffected** — `adopts[]` is type-definition provenance, not instance payload (CONFORMANCE §9 wire-compat not impacted). | Any externally-authored type using `adopts[]` adds `license` + `licenseCompatibility` ∈ `{compatible-reference, compatible-vendor, reference-only}` + `source`. In-repo `Data.Database` / `Compute.Cluster` backfilled. |
| 2026-06-27 | meta-schema (`udlm/0.1`) edited in place; all 19 types touched | **camelCase consolidation** — renamed the last snake_case meta-schema keys: `origination_timestamp`→`originationTimestamp` (in every type's `metadata`), and `deprecation.migration_guidance`→`migrationGuidance`, `deprecation.replacement_uuid`→`replacementUuid`. Adopts the camelCase data-model casing convention (`registry/naming-conventions.md` §4). | **Yes — backward-incompatible** (required key renamed). A type still using `origination_timestamp` no longer validates. **Wire/instance format aligns to camelCase** going forward. | Rename `origination_timestamp`→`originationTimestamp` (and the two `deprecation.*` keys) in any externally-authored type. All in-repo types updated. **⚠️ SUPERSEDED same-day by the snake_case reversal below — do not apply this row.** |
| 2026-06-27 | meta-schema (`udlm/0.1`) edited in place; **every** type, schema, instance, and provider doc touched | **snake_case reversal (supersedes the camelCase row above).** All native data-model keys recased camelCase→`snake_case` (`resourceType`→`resource_type`, `conformsTo`→`conforms_to`, `deviceClass`→`device_class`, `lifecycleState`→`lifecycle_state`, `originationTimestamp`→`origination_timestamp`, `migrationGuidance`→`migration_guidance`, … 92 keys; initialisms lowercased, e.g. `podCIDR`→`pod_cidr`). JSON Schema keywords (`allOf`, `additionalProperties`, …) untouched; **adopted-standard names keep source casing as VALUES** (`standard_name: "SerialNumber"`). New rule §23a (adopt-by-reference casing). | **Yes — backward-incompatible** (every key renamed). | **Rationale:** UDLM is consumed natively (canonical data model), and the DCM API is AEP-bound (`aep.dev`, snake_case); native consumption + AEP jointly force one casing. The camelCase decision (driven by research that hadn't accounted for AEP) was reverted. Externally-authored types: recase native keys to `snake_case`, keep adopted source names as `standard_name`/`x-standard`/`aliases` values. All in-repo artifacts done; `tools/validate.py` green. See `naming-conventions.md` §4. |

## Serialization — JSON **and** YAML, natively

The normative *model* is JSON Schema 2020-12; the *serialization* is not privileged. A registry
document MAY be authored in **JSON or YAML** — they parse to the same document and validate against
the same meta-schema (`compute.container.yaml` and `compute.virtual-machine.json` in this registry
prove it). JSON is the canonical *wire/interchange* form (schema-sharing); YAML is offered for
authoring ergonomics. Tooling (`tools/validate.py`, `tools/compat-check.py`) loads both.

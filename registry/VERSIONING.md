# UDLM Registry — Versioning & Compatibility Policy

UDLM versions two things independently. Getting this separation right is what lets the spec
evolve without breaking the registry, and lets a resource type evolve without a spec bump.

## The two axes

| Axis | What it versions | Scheme | Rule |
|---|---|---|---|
| **SPEC** | the UDLM meta-model: this meta-schema, the contracts, four-state lifecycle, identifier scheme | `MAJOR.MINOR` semver | Peers conformant to the same **MAJOR** are wire-compatible (CONFORMANCE.md §9). Cross-major interop = support both majors concurrently. |
| **ENTITY** | each Resource Type Specification | `MAJOR.MINOR.REVISION` | Immutable once published; any change publishes a new version. |

**The binding:** every entity declares `conforms_to: udlm/<spec MAJOR.MINOR>` — its `apiVersion`.
That tells the registry which meta-schema version validates it. Downstream, **constraint
profiles / catalog items (E1)** and **realized instances (E5)** pin the *entity* version they
were built from, so drift is measured against the exact contract that produced them.

**The publish law (ADR-051), stated beside the rules it completes:** a published
(identity, version) pair is immutable. Any content change — semantic, doc-only, anything —
ships at least a REVISION bump; publishing different bytes under an already-published pair is
refused (`tests/check_identity_integrity.py` R2, via the pin manifest). The bump *size* is
classified by the entity-semver table below; the bump *existence* is this law.

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

**The pre-1.0 bump floor (one rule, gate-enforced):** a MAJOR-classified (breaking) change is
accepted under a **MINOR** bump until 1.0 — never under a REVISION. This is exactly what
`tests/ci_compat_gate.py` enforces ("MAJOR relaxed to MINOR"); any prose stating the bump a
breaking change requires must cite this floor, not post-1.0 MAJOR semantics. Bumping an entity
to `1.0.0` is never the remedy for a breaking change — 1.0 is earned by the stability
commitment above, and an entity crossing it enters the strict regime.

### Cutting the spec `0.1 → 1.0` — the mechanical procedure

The 1.0 exit criteria are enumerated in [`UDLM-0.1-SCOPE.md`](UDLM-0.1-SCOPE.md). Once they are met,
declaring 1.0 is a **repo-wide, mechanical re-stamp** — not a redesign:

1. **Re-stamp `conforms_to`** on every type spec, schema, and instance: `udlm/0.1 → udlm/1.0`.
2. **Re-mint each `$id` spec-segment** to match (`.../udlm/0.1/... → .../udlm/1.0/...`).
   `tests/validate_registry.py` enforces `$id` spec-segment == `conforms_to`, so 1 and 2 move together
   or CI fails.
3. **Bump the meta-schema `$id`** (`resource-type-spec.schema.json` and the record schemas) to `udlm/1.0`.
4. **Entity versions do NOT rebase.** `conforms_to` is the SPEC axis; the per-entity `version` is the
   independent entity axis (the two-axes rule above). A type at `0.6.0` stays `0.6.0` under `udlm/1.0`.
5. **Tag the repo `udlm/1.0`.** From this tag, "same SPEC-MAJOR = wire-compatible" becomes a binding
   promise; the next breaking spec change is `udlm/2.0`.

This is deliberately deferred until the exit criteria pass — re-stamping early would spend the 1.0
compatibility promise on an unfinished surface.

## Lifecycle vs. maturity — two independent axes

A definition has two orthogonal signals; don't conflate them into one field:

- **Lifecycle = `status`** (`active | deprecated | retired`) — where a *published* version sits in its
  life. This is the meta-schema field.
- **Maturity / stability = the version itself** — `0.x` is pre-stable (experimental/incubating), `1.0`
  is the earned-stable milestone. This is exactly the **Kubernetes** model (maturity rides the version —
  `v1alpha1` / `v1beta1` / `v1` — while deprecation is tracked separately), not a second status enum.
  So "how baked is this?" is read from the version, and a thing can be `active` **and** still `0.x`
  (active-but-not-yet-stable) without overloading `status`.
- **Review stage** (`developing` / `proposed` / accepted) is a **third** thing — the governance
  *workflow* an artifact moves through on its way into the registry (`governance/registry-governance.md`
  §3). It is **not** a `status` value: a definition only appears in the validated registry once accepted
  (`status: active`). Don't put review states in `status`.

An explicit per-type `stability` field (for when one type is battle-tested while the spec is still
`0.x`) is a deferred candidate — see SPEC-DESIGN-REQUIREMENTS *Candidate / deferred data points*.

## Entity semver — what bumps what

| Change | Bump |
|---|---|
| Add an **optional** field; add an **output**; add a relationship; **loosen** a numeric/string range | **MINOR** |
| Add an **enum value** to a field marked `x-extensible-enum: true` | **MINOR** |
| Add an **enum value** to a closed (unmarked) enum — consumers that exhaustively switch on values break (Kubernetes api_changes rule) | **MAJOR** |
| **Remove/rename** a field; make an existing field **required**; **narrow** validation (tighter enum/range); remove an output/relationship; change `entity_type`/`portability`/lifecycle | **MAJOR** |
| **Change a field's declared `type`** (string→object, integer→string, …) — every existing instance of the field is invalidated | **MAJOR** |
| Narrow a class element's **scope** (Base→Type, Type→Provider) — the derived portable surface of every carrier shrinks, even with no schema-shape change (ADR-045) | **MAJOR** |
| Docs, descriptions, metadata, non-semantic edits | **REVISION** |

A **MAJOR** bump is a breaking change: the prior version moves to `deprecated`, and the new
version's `deprecation`-linked predecessor MUST carry `migration_guidance`. Consumers pinned to
the old major keep working until it is `retired`.

## Deprecation lifecycle (universal model, foundations/layering-and-versioning.md)

```
active ──► deprecated ──► retired
```
- `deprecated` versions still resolve and still serve pinned consumers; they carry
  `deprecation.{date, reason, replacement_uuid, migration_guidance}`.
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

**Scope: the consumer edge.** Version constraints govern how *consumers* — estate records,
downstream registries, external tooling — reference registry entities. **Inside the registry,
none of this applies to class references** (ADR-045): a Type or Provider Class references its
parent by handle only and compiles against the release's current version; the registry ref
(commit) is the sole intra-registry pin. The revision store behind consumer pins is the
registry's git history — a `thing@version` or `thing@sha256:<hex>` pin (ADR-051) resolves within
the registry ref (or ref range) the consumer declares it consumes, which is how a pin can be
legally *behind* the current ref while a pin resolving in no declared ref is refused as unknown.

- Reference a type by `resource_type` + a version constraint: exact (`1.2.0`), minor-floating
  (`~1.2`), or major-floating (`^1`). Default resolution returns the latest **active** version
  satisfying the constraint.
- `deprecated` versions resolve only to consumers that pin them; `retired` versions do not resolve.

## Identity, version, digest

*(Supersedes the former § "UUID rotation" — ADR-051. The rotating-uuid doctrine is retired;
uuids existing at the ruling froze in place, and history rows describing past rotations stand
as written.)*

Three fields, three jobs — never one field doing two (the Kubernetes
`uid`/`generation`/`resourceVersion` split):

- **UUID = identity.** The uuid names the thing, is frozen at creation, and is never reused.
  No edit ever changes one; nothing about content is inferable from one.
- **Version = the compat contract, under the publish law.** The bump table below is
  unchanged; in addition, **(identity, version) is immutable once published** — any content
  change ships a version bump (≥ REVISION), and republishing an already-published
  (identity, version) with different bytes is refused (the npm publish law).
- **Digest = change transparency.** sha256 over the RFC 8785 (JCS) canonical form of the
  parsed document (JSON and YAML digest identically). Artifacts never carry their own digest
  (the OCI referrer rule): digests live in the generated
  [`pin-manifest.json`](pin-manifest.json), provenance blocks, attestations, and promotion
  evidence.
- **Pins are `thing@version` (human-legible) or `thing@sha256:<hex>` (exact),** both
  first-class; a profile may require digest pins (fsi).
- **Two document families.** Mutable-in-place documents (type specs, providers, policies,
  profiles) keep their uuid and bump their version on edit. Immutable record streams
  (decision records, layers, audit records, accreditations, regeneration manifests,
  finding-routing records) change by publishing a **new record** (new identity uuid) with
  `supersedes` naming the predecessor; editing or deleting a published record is refused.

Gate failures (`tests/check_identity_integrity.py`): a changed mutable document whose uuid
moved or whose version did not; a republished (identity, version) with different bytes; an
edited or deleted immutable record; a changed nested provider/capability identity.
`registry/tools/generate_pin_manifest.py --check` holds the manifest current and append-only.

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
| 2026-07-27 | `common-elements.schema.json`, `realized-entity.schema.json`, `accreditation.schema.json` (SPEC `udlm/0.1`) edited in place | **ADR-051 pin surface:** `$defs/Reference` gains optional `target_version` + `target_digest` (the `thing@version` / `thing@sha256:<hex>` pin pair) and optional authored `target_authority` (dotted ADR-038 §10 form; closes standing-gap §4 — boundary policy matches the owning authority without dereferencing); realized entities gain optional `type_digest` beside `type_version`; accreditations gain optional `attested_digests` (in-toto subject digests, exact-by-default). Description-only alignment on `provider-adopted-standards` (provider/capability uuids = frozen identity), `layer`, and `data-reference` (immutable-record family wording). | **No** — all additive optional fields; description edits carry no shape change. | None required. Consumers that want exactness start recording digests; nothing existing is invalidated. |
| 2026-07-25 | `audit-record.schema.json`, `audit-leaf.schema.json`, `commit-log-entry.schema.json` (SPEC `udlm/0.1`) edited in place | **Refusal enforcement surface:** the closed audit `action` vocabulary gains `REFUSE` (`AUD-023` — a refusal is recorded as an operational fact, not inferred from an `EVALUATE` record whose outcome was negative); the closed error-code vocabulary (`contracts/error-model.md` §3.2) gains ten codes for the measured refusal surfaces (`authz.cross_tenant_unauthorized`, `validation.reference_not_found`, `validation.inline_credential_material`, `validation.binding_undeclared_output`, `validation.version_bump_insufficient`, `validation.intra_registry_version_pin`, `validation.pin_unresolvable`, `policy.sovereignty_egress_denied`, `policy.field_scope_violation`, `policy.promotion_diff_unapproved`). No existing value's semantics change. | **Yes, formally** — an addition to a closed enum is MAJOR by the bump table, since a consumer switching exhaustively on `action` or `type` meets an unhandled value. Carried in place by the pre-1.0 exception; no existing record or envelope is invalidated. | A consumer that switches exhaustively on the audit `action` enum or on the error `type` vocabulary adds a default branch; no stored record changes shape. |
| 2026-07-25 | 18 types REVISION-bumped (`Access.IdentityEscrow` 0.1.1, `Compute.Container` 0.5.3, `Compute.VirtualMachine` 0.6.4, `Hardware.NetworkInterface` 0.9.3, `Identity.Group` 0.2.2, `Identity.Person` 0.3.2, `Identity.ServiceAccount` 0.3.2, `Network.Gateway` 0.4.4, `Network.IPAddress` 0.6.2, `Network.IPAddressPool` 0.3.2, `Network.Switch` 0.4.4, `Platform.Namespace` 0.3.5, `Platform.NodePool` 0.3.4, `Platform.ResourceQuota` 0.3.2, `Security.CredentialRef` 0.3.2, `Software.Service` 0.4.3, `Storage.FileShare` 0.3.4, `Storage.Volume` 0.5.3) | **Registry structure by class:** `resource-types/` grouped into per-class directories (dotted `resource_type` → lowercased first segment; single-word types → lowercased `family`), `providers/` grouped by `provider.kind` — rule in `resource-types/README.md`. Filenames unchanged; the only content change is the moved specs' relative `$ref`s deepening one level (`../` → `../../`), so exactly those 18 files rotate uuid + REVISION per the UUID-rotation rule; the other 32 moved files are byte-identical and keep uuid/version (the no-op rule). Complete old→new map: [`renames.yaml`](renames.yaml) — the first exercise of the rename-map discipline; the base-ref-diffing gates consult it. **⚠️ Doctrine note (appended 2026-07-27): the UUID-rotation rule this row applied was superseded by ADR-051 — the 18 uuids minted here are now frozen identities and never rotate again; this row stands as history.** | **No** — file location is navigation, not identity; `$ref` targets, schema shapes, and wire/instance format are unchanged. | Resolve any hardcoded spec file path through `registry/renames.yaml`; identity references (`resource_type`, `$id`, uuid) are unaffected by the move. |
| 2026-07-24 | 19 types REVISION-bumped (`Automation.Job` 0.4.1, `Compute.Cluster` 0.4.1, `Compute.Container` 0.5.1, `Compute.VirtualMachine` 0.6.1, `Hardware.BMC` 0.4.1, `Hardware.BiosProfile` 0.4.1, `Network.AddressService` 0.4.1, `Network.ConnectionProfile` 0.3.1, `Network.DNSZone` 0.3.1, `Network.Gateway` 0.4.1, `Network.Switch` 0.4.1, `Observability.LogShipper` 0.3.1, `Platform.Hub` 0.1.1, `Platform.Namespace` 0.3.2, `Platform.NodePool` 0.3.1, `Platform.StorageClass` 0.3.1, `Security.DirectoryService` 0.4.1, `Software.Service` 0.4.1, `Storage.FileShare` 0.3.1) | **Product-name neutrality sweep** (SPEC-DESIGN §35 tightening): products/vendors as actors or examples replaced with generic archetypes in descriptions, context blocks, and example values; product names remain only in `adopts[]`/`aliases[]` attribution. Description-only — no schema, field, enum, or relationship change. | **No** — description-only; wire/instance format unaffected. | None required. |
| 2026-07-06 | `Network.Switch` → **0.1.1**; `Hardware.NetworkInterface` → **0.5.1**; `realized-entity.schema.json` (SPEC `udlm/0.1`) edited in place | Wave-2 enum/single-source unifications: **(a)** description-only rename sweep `connected_to`→`connects_to` in the two types' description strings (the relation itself was already `connects_to`; REVISION bumps); **(b)** instance provenance `source.kind` enum extended `[layer, policy, actor, provider]` → `[layer, policy, actor, provider, discovery, rehydration, override]` (data-model-core §6/§7; 'consumer' maps to 'actor') + optional `operation_type` (`set|merge|remove`) and `sequence` on provenance entries (ordered modification chains). | **No** — (a) description-only; (b) additive enum widening + optional fields (existing instances validate unchanged). | None required. |
| 2026-07-06 | `realized-entity.schema.json` (SPEC `udlm/0.1`) edited in place; `Automation.Job` → **0.2.0**; 9 types MINOR-bumped | Wave-1 conformance-to-core sweep: **(a)** `time_source` now REQUIRED on realized/discovered snapshots (data-model-core §6 — no fabricated precision); **(b)** instance `resource_type` pattern loosened to allow single-segment names (matches the type schema); **(c)** `Automation.Job` `references` target retargeted `Compute`→`Compute.VirtualMachine` (bare category was not a registered type; edge is informational — affected entities may be any type) + named `depends_on` edges; **(d)** relationship `name`s added to the 9 multi-same-kind types (additive MINOR). | **(a) Yes** — an instance whose realized/discovered snapshot lacks `time_source` no longer validates (would be MAJOR post-1.0; carried in-place by the pre-1.0 exception). **(c) Yes** under the compat rules (relationship retarget). (b)/(d) non-breaking. | Add `time_source` (clock attribution) to realized/discovered snapshots — in-repo `instances/orders-db.json` backfilled. Instance edges citing the Automation.Job `references` edge keep working (informational; any-type note on the relationship). |
| 2026-06-26 | `Data.Database` & `Compute.Cluster` → **0.1.1**; meta-schema (SPEC `udlm/0.1`) edited in place | `adopted_standard_ref` (`resource-type-spec.schema.json`) now requires `source`, `license`, `license_compatibility`; `identity_join` relaxed to optional (SPEC-DESIGN-REQUIREMENTS §22–23). | **Yes — backward-incompatible.** An `adopts[]` entry without the license verdict no longer validates (would be a MAJOR post-1.0; carried in a `0.1.1` REVISION by the pre-1.0 exception above). **Wire/instance format is unaffected** — `adopts[]` is type-definition provenance, not instance payload (CONFORMANCE §9 wire-compat not impacted). | Any externally-authored type using `adopts[]` adds `license` + `license_compatibility` ∈ `{compatible-reference, compatible-vendor, reference-only}` + `source`. In-repo `Data.Database` / `Compute.Cluster` backfilled. |
| 2026-06-27 | meta-schema (`udlm/0.1`) edited in place; all 19 types touched | **camelCase consolidation** — renamed the last snake_case meta-schema keys: `origination_timestamp`→`originationTimestamp` (in every type's `metadata`), and `deprecation.migration_guidance`→`migrationGuidance`, `deprecation.replacement_uuid`→`replacementUuid`. Adopts the camelCase data-model casing convention (`registry/naming-conventions.md` §4). | **Yes — backward-incompatible** (required key renamed). A type still using `origination_timestamp` no longer validates. **Wire/instance format aligns to camelCase** going forward. | Rename `origination_timestamp`→`originationTimestamp` (and the two `deprecation.*` keys) in any externally-authored type. All in-repo types updated. **⚠️ SUPERSEDED same-day by the snake_case reversal below — do not apply this row.** |
| 2026-06-27 | meta-schema (`udlm/0.1`) edited in place; **every** type, schema, instance, and provider doc touched | **snake_case reversal (supersedes the camelCase row above).** All native data-model keys recased camelCase→`snake_case` (`resourceType`→`resource_type`, `conformsTo`→`conforms_to`, `deviceClass`→`device_class`, `lifecycleState`→`lifecycle_state`, `originationTimestamp`→`origination_timestamp`, `migrationGuidance`→`migration_guidance`, … 92 keys; initialisms lowercased, e.g. `podCIDR`→`pod_cidr`). JSON Schema keywords (`allOf`, `additionalProperties`, …) untouched; **adopted-standard names keep source casing as VALUES** (`standard_name: "SerialNumber"`). New rule §23a (adopt-by-reference casing). | **Yes — backward-incompatible** (every key renamed). | **Rationale:** UDLM is consumed natively (canonical data model), and the DCM API is AEP-bound (`aep.dev`, snake_case); native consumption + AEP jointly force one casing. The camelCase decision (driven by research that hadn't accounted for AEP) was reverted. Externally-authored types: recase native keys to `snake_case`, keep adopted source names as `standard_name`/`x-standard`/`aliases` values. All in-repo artifacts done; `tools/validate.py` green. See `naming-conventions.md` §4. |

## Serialization — JSON **and** YAML, natively

The normative *model* is JSON Schema 2020-12; the *serialization* is not privileged. A registry
document MAY be authored in **JSON or YAML** — they parse to the same document and validate against
the same meta-schema (`compute.container.yaml` and `compute.virtual-machine.json` in this registry
prove it). JSON is the canonical *wire/interchange* form (schema-sharing); YAML is offered for
authoring ergonomics. Tooling (`tools/validate.py`, `tools/compat-check.py`) loads both.

## Enum extensibility

Adding an enum value looks additive but breaks consumers that exhaustively handle known values
(adopted from the Kubernetes API-change rules, where even enum additions are classified
backward-incompatible unless the field is documented as extensible). A type spec opts a field
into open-world semantics by annotating it `x-extensible-enum: true` next to the `enum` —
consumers of such fields MUST tolerate unknown values. Unmarked enums are closed: additions are
MAJOR. *Grandfather note:* `Hardware.NetworkInterface.device_class` gained values at 0.2.0/0.3.0
under the previous rule; it is now marked extensible (0.4.0) rather than retroactively re-versioned.

- **2026-07-07 (wave 3.8):** `Storage.Volume` 0.1.0 authored (consumable volume; fills the #271 storage gap). `Data.Database` 0.1.1 → **0.2.0** — `resources` now required (matches the dcm-project catalog DatabaseSpec) and storage/host relationships added; requiring a previously-optional field is a compat break, taken under the pre-1.0 exception.

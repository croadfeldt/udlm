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

**Who confers `1.0` (maintainer ruling, 2026-07-27):** `1.0` is **not a date the maintainer picks
and not a milestone declared unilaterally — it is conferred by engineering acceptance** (the
ratification pass tracked at #217). A "surface complete" state — even the September surface — is
still **`0.1` work** until engineering accepts it; readiness is a *candidacy* for that review, not a
self-promotion. Every ADR in this repository is `Proposed` for exactly this reason: the model is
built and measured, and 1.0 is what the acceptance confers on it, not what the authoring declares.

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

## Pre-1.0 versioning discipline

While the spec is `0.x` the surface is still being **defined**, so changes are *expansion of the v0.x
surface*, not refinement of a released contract (see "Spec status" above).

**Pre-1.0 we do NOT follow the full versioning rules above.** Those rules (MAJOR for breaking changes + deprecation window) are the *post-1.0* discipline that protects consumers
pinned to a released contract — which don't exist yet. While `0.x`:

- Versions still **advance** (we bump the REVISION) so a reader can tell a definition changed, **but a
  `0.x` REVISION/MINOR MAY carry backward-incompatible (breaking) changes** that post-1.0 would require
  a MAJOR + deprecation. No deprecation ceremony is performed pre-1.0; the version bump and the
  compat gate's priced diff are the record of the change.


## Serialization — JSON **and** YAML, natively

The normative *model* is JSON Schema 2020-12; the *serialization* is not privileged. A registry
document MAY be authored in **JSON or YAML** — they parse to the same document and validate against
the same meta-schema. In practice the authored surface (`registry/classes/`) is YAML and every
served spec (`registry/generated/`) is JSON — the same document either way. JSON is the canonical
*wire/interchange* form (schema-sharing); YAML is offered for authoring ergonomics. Tooling
(`tools/validate.py`, `tools/compat-check.py`) loads both.

## Enum extensibility

Adding an enum value looks additive but breaks consumers that exhaustively handle known values
(adopted from the Kubernetes API-change rules, where even enum additions are classified
backward-incompatible unless the field is documented as extensible). A type spec opts a field
into open-world semantics by annotating it `x-extensible-enum: true` next to the `enum` —
consumers of such fields MUST tolerate unknown values. Unmarked enums are closed: additions are
MAJOR. *Grandfather note:* `Hardware.NetworkInterface.device_class` gained values at 0.2.0/0.3.0
under the previous rule; it is now marked extensible (0.4.0) rather than retroactively re-versioned.

- **2026-07-07 (wave 3.8):** `Storage.Volume` 0.1.0 authored (consumable volume; fills the #271 storage gap). `Data.Database` 0.1.1 → **0.2.0** — `resources` now required (matches the dcm-project catalog DatabaseSpec) and storage/host relationships added; requiring a previously-optional field is a compat break, taken under the pre-1.0 exception.

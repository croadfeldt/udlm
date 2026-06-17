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

## Entity semver — what bumps what

| Change | Bump |
|---|---|
| Add an **optional** field; add an **output**; add a relationship; **widen** validation (looser enum/range) | **MINOR** |
| **Remove/rename** a field; make an existing field **required**; **narrow** validation (tighter enum/range); remove an output/relationship; change `entityType`/`portability`/lifecycle | **MAJOR** |
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

- Reference a type by `resourceType` + a version constraint: exact (`1.2.0`), minor-floating
  (`~1.2`), or major-floating (`^1`). Default resolution returns the latest **active** version
  satisfying the constraint.
- `deprecated` versions resolve only to consumers that pin them; `retired` versions do not resolve.

## Serialization — JSON **and** YAML, natively

The normative *model* is JSON Schema 2020-12; the *serialization* is not privileged. A registry
document MAY be authored in **JSON or YAML** — they parse to the same document and validate against
the same meta-schema (`compute.container.yaml` and `compute.virtual-machine.json` in this registry
prove it). JSON is the canonical *wire/interchange* form (schema-sharing); YAML is offered for
authoring ergonomics. Tooling (`tools/validate.py`, `tools/compat-check.py`) loads both.

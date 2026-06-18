# UDLM Resource Type Registry

The registry is the concrete instantiation of UDLM's **Resource Type Specifications** — the
versioned, formal definitions that the spec (prose, in `../`) describes but does not, until now,
contain. Each entry is a vendor-neutral definition of a resource type's field schema, constraints,
typed outputs, lifecycle, and allowed relationships. Providers implement against a version; catalog
items and constraint profiles project over them.

## Layout
```
registry/
  resource-type-spec.schema.json   # the meta-schema every entry MUST validate against
  VERSIONING.md                    # the two-axis versioning + compatibility policy
  realized-entity.schema.json      # the INSTANCE meta-schema (four states + provenance + ownership)
  resource-types/                  # TYPE definitions — one file per entity type, JSON or YAML
    compute.virtual-machine.json   #   Resource family (Category.Type names)
    compute.cluster.json
    data.database.json
    network.ip-address.json
    compute.container.yaml          # ← YAML; semantically identical, same meta-schema
    observability.cost-meter.json   #   Process entityType — metering/cost over other resources (dcm#60)
    capability.json                 # ← Knowledge family (single-segment name; curation lifecycle)
  instances/                       # INSTANCE records (realized entities) — e.g. orders-db.json
  tools/
    validate.py                    # valid-by-construction: every entry vs the meta-schema
    compat-check.py                # classify a version delta + enforce the declared bump
```

## Design, and how it maps to UDLM
- **`spec` is desired state, `outputs` is observed state.** A type's `spec` field schema is the
  **Intent/Requested** contract a consumer fills; its typed `outputs` are the **Realized/Discovered**
  values a provider publishes. This is the same desired-vs-observed split Kubernetes enforces with
  `spec`/`status` — here it falls straight out of UDLM's four states.
- **`conformsTo` + `version` = two version axes.** `conformsTo: udlm/1.0` binds the entry to a SPEC
  version (its `apiVersion`); `version` is the entry's own `MAJOR.MINOR.REVISION`. See `VERSIONING.md`.
- **Relationships are first-class** (`depends_on`, `binds_to`, …) — the substrate the composite model
  (`../entities/composite-service-model.md`) builds its dependency DAG from.
- **JSON and YAML are both native.** The normative *model* is JSON Schema 2020-12; serialization is
  not privileged. Author in whichever you prefer — the tooling loads both.

## Two families
The meta-schema covers **both entity-type families** (`foundations/entity-type-families.md`):
**Resource** (provisioned by a provider — `Category.Type` names, four-state lifecycle archetype
`provisioning`) and **Knowledge** (curated, never provider-realized — single-segment names like
`Capability`, lifecycle archetype `curation`). `family` + `entityType` are family-conditional in the
meta-schema; the `resource-types/` directory holds both (the dir name predates the Knowledge family).
`capability.json` is the worked Knowledge example (anchored by DAV, `entities/knowledge-family.md`).

## Adding a resource type
1. Create `resource-types/<name>.{json,yaml}` — `<category>.<type>` (Resource) or `<type>` (Knowledge).
2. Fill the required fields (`conformsTo`, `uuid` [new UUIDv4], `resourceType`, `version`, `family`,
   `entityType`, `portability`, `status`, `metadata`, `spec`, `outputs`).
3. `python3 tools/validate.py` — must pass (valid-by-construction).
4. For a change to an existing type, `python3 tools/compat-check.py <old> <new>` — the declared
   `version` bump must be ≥ the required bump.

## Conformance
`tools/validate.py` is the gate; wire it into CI. An entry that does not validate against the
meta-schema is not a conformant Resource Type Specification.

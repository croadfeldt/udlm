# UDLM Resource Type Registry

The registry is the machine surface of the spec: the versioned, formal definitions of every
resource type, and the schemas every record kind validates against. **Classes are the one
authored surface** (`classes/` — ADR-061's hierarchy); the flat specs consumers read are
**generated projections** (`generated/`, never edited by hand). Providers implement against a
served version; catalog items and constraint profiles project over them.

## Layout
```
registry/
  class.schema.json                # the CLASS meta-schema — classes/ is the authored surface
  resource-type-spec.schema.json   # the flat-spec meta-schema generated/ validates against
  classes/<family>/…               # ALL definitions (ADR-061: base = dir + _base.yaml;
                                   #   type/provider = leaf file until it gains children)
  generated/                       # the SERVED flat specs — compiled, one per type, never authored
  profiles/                        # the deployment PROFILES — activatable postures (six built-in)
  instances/                       # worked example records (realized entities, policies, layers, …)
                                   #   and the shipped decision/taxonomy records
  realized-entity.schema.json      # the instance meta-schema (four states + ownership)
  VERSIONING.md                    # two-axis versioning + the publish law
  pin-manifest.json                # the digest referrer behind the publish law (append-only)
  rule-id-registry.yaml            # every normative rule family and its one home file
  standards-adoption-register.md   # every adoption decision (what/why/license) — ADOPT-001
  standards-catalog.md             # conformance obligations per external standard
  tools/                           # generate_class_specs, validate, compat-check, pin manifest, …
```

## How it maps to UDLM
- **`spec` is desired state, `outputs` is observed state** — the Intent/Requested contract a
  consumer fills vs the Realized/Discovered values a provider publishes; the Kubernetes
  `spec`/`status` split, falling straight out of the four states.
- **`conforms_to` + `version` = two version axes** (`VERSIONING.md`): the SPEC binding and the
  entry's own `MAJOR.MINOR.REVISION`, under the publish law — a published (identity, version)
  pair is immutable.
- **JSON and YAML are both native.** Classes are authored in YAML; every served spec is JSON —
  the same document either way (the normative model is JSON Schema 2020-12).

## Adding a resource type
Author a **class**, not a flat file — the full procedure is
[`docs/authoring/scoped-class.md`](../docs/authoring/scoped-class.md) (which gates enforce what),
the layout grammar is [ADR-061](../docs/adr/ADR-061-class-directory-hierarchy.md) (path = verified
projection of family + name segments), and the rules every definition must satisfy are
[`SPEC-DESIGN-REQUIREMENTS.md`](SPEC-DESIGN-REQUIREMENTS.md). In one breath: create the class
YAML under `classes/<family>/…`, fill `adopts[]` with source + license, reuse common-elements,
ship a `spec.examples` entry, run `python3 registry/tools/generate_class_specs.py`, and commit
the generated spec with it — `bash scripts/signoff.sh` runs every gate that will judge it.

## Conformance
`registry/tools/validate.py` + the CI suite are the gate: a definition that does not validate,
compile, and pass the class gates is not a conformant Resource Type Specification.

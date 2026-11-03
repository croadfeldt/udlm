# Authoring a layer

**What this is.** A layer is a record of values an estate applies to requests before a provider
sees them: defaults, bounds, and who may change them. Layers stack in a fixed order, lowest
authority first, and the merged result carries per-field provenance saying which layer set what.
This page is the procedure for writing one. The contract is
[`docs/spec/foundations/layering-and-versioning.md`](../spec/foundations/layering-and-versioning.md);
the schema is [`registry/layer.schema.json`](../../registry/layer.schema.json).

> **Read once first:** [`../../CONTRIBUTING.md`](../../CONTRIBUTING.md) and [`README.md`](README.md)
> (the universal contract).

## 1. When to use it — and when not

Write a layer when one value should be filled in, or bounded, for many requests at once: an
organisation's default backup retention, a team's standard VM size, a compliance floor nobody below
it may lower.

Not a layer:

- **The value belongs to one thing.** Put it in that thing's intent record.
- **You are deciding what to do about a value.** That is a policy: [`policy.md`](policy.md).
- **A governed list of terms** (storage tiers, OS images). That is reference data:
  [`reference-data.md`](reference-data.md). It uses the same schema with `layer_type: reference_data`.
- **The shape of a thing** (which fields a VM has). That is a class: [`scoped-class.md`](scoped-class.md).

UDLM ships no defaults (NDF-001). A layer in this repository is a worked example with `example.com`
content; the values your estate wants live in your estate's own layers.

## 2. The steps, in order

1. **Pick the type.** `layer_type` and `precedence_class` carry the same word. Lowest authority first:

   | Type | Who writes it | What it holds |
   |---|---|---|
   | `base` | platform | where every chain begins; the universal fields of one resource type |
   | `core` | standards or compliance owners | the organisation's floors and ceilings |
   | `intermediate` | a business unit or team | customisation on top of core |
   | `service` | a service owner | what one service needs |
   | `request` | the consumer | values on one request; override all data layers |
   | `policy` | policy owners | applied over the merged result; compliance-class rules override everything |

2. **Copy the nearest example** from §4 into `registry/examples/`, or into your estate's own store.
3. **Fill the envelope.** New `uuid` (v4), a `handle`, `name`, `description`, `version: 1.0.0`,
   `tenant_uuid`, `status: {state: active}`, `domain`, and `contributor` (who may author it and
   what review it needs). A layer with `domain: resource_type` must name its `resource_type`.
4. **Say what it sets.** `fields`, in the shape of the class it applies to. Only values the estate
   actually wants; a silent layer sets nothing.
5. **Say what it bounds** (optional). `limits`, keyed by field path, each a list of clauses with
   `min`, `max`, `step` and a `reason`. Absent means unbounded, never empty.
6. **Say what it builds on** (optional). `extends`, a list of `layer: uuid/<uuid>@<version>` with a
   `reason`, and an optional `when` (equality only). Your own limits must sit inside every parent's.
7. **Say where it applies** (optional). `covers` names which resources this layer may inject into;
   `applies_on` names during which scenarios. Both are URF filters.
8. **Change it later as a new record.** A published layer is never edited. A change is a new file:
   new `uuid`, higher `version`, and `supersedes` naming the old uuid.

## 3. Completeness checklist — and the gate that enforces each

| Must be true | Gate |
|---|---|
| Validates against the layer schema | `registry/tools/validate.py` |
| Every `extends` target is a real layer; no cycles | `tests/check_layer_limits.py` LIM-001, LIM-002 |
| Your `limits` sit inside every ancestor's envelope | `tests/check_layer_limits.py` LIM-003 |
| Your `fields` satisfy your own `limits` | `tests/check_layer_limits.py` LIM-004 |
| No field's clauses intersect to nothing | `tests/check_layer_limits.py` LIM-005 |
| A shipped example says in its header what it shows | `tests/check_example_coverage.py` ECV-001, ECV-002 |
| No private hostnames or addresses; RFC 5737 ranges only | `tests/check_estate_tokens.py` |

UDLM checks the structure. It does not enforce a bound at runtime; a `validation` policy reads the
assembly's limit facts and refuses, naming the layer, the owner, the field and the clause (LAY-010).
The worked policy is `registry/examples/example-policy-layer-limit.yaml`.

## 4. A worked pointer

| Want | Copy |
|---|---|
| A base layer with universal defaults | `registry/examples/example-layer-base.yaml` |
| A layer that declares bounds | `registry/examples/example-layer-limits-baseline.yaml` |
| A layer that extends two parents, one conditionally | `registry/examples/example-layer-extends-multi.yaml` |
| An organisation customisation layer | `registry/examples/example-layer-intermediate.yaml` |
| A request-scoped layer | `registry/examples/example-layer-request-scoped.yaml` |
| A layer that references governed data | `registry/examples/example-layer-referencing.yaml` |

## 5. Run the gates

From the repo root:

```
python3 registry/tools/validate.py
python3 tests/check_layer_limits.py
```

A pass looks like:

- **validate.py** — one `ok   <your file>  — layer <name> (<type>) <uuid prefix>` line under
  `== examples ==`, and no `FAIL` line.
- **check_layer_limits.py** — `layer limits: N layer(s), …` then
  `OK — lineage resolves, no cycles, every envelope contained and satisfiable`, exit 0.

While you work, run just these through signoff:

```
./scripts/signoff.sh --only 'valid-by-construction|LAY-009|estate-token|ECV-001'
```

`./scripts/signoff.sh` with no `--only` runs the full gate set; do that before you open a PR.

# Authoring a resource type

**What this gets you.** A new resource type (a VM, a Volume, a DNSZone) that validates by construction,
ships with its story, and passes CI on the first push. Follow the steps in order and every gate named
below goes green; skip one and the gate that owns it names it back. This is the procedure that landed
the current 48 specs — the same one, written down.

A **resource type** is the versioned contract for one kind of thing a provider realizes: its field
schema (the Intent/Requested wire shape), its typed Realized `outputs`, and the standards it adopts. It
lives in `registry/resource-types/<domain>/<type>.yaml` (or `.json`) and validates against
`registry/resource-type-spec.schema.json` — read that meta-schema once before you start; it is the law
every step here satisfies.

## 1. When to use it — and when not

Reach for a resource type when you are modeling **a thing that is maintained in a state** — provisioned,
observed, then reconciled — and a provider naturalizes it into a native object. VM, Volume, Pool,
DNSZone, Switch: each is a noun with a lifecycle.

Do **not** author a resource type when:

- It is **a job or operation with a blast-radius** (a patch run, a backup) — that is a process. Follow
  [`process.md`](process.md) (the Process-family Class, or the `Automation.Job` resource type for the
  simple case).
- It is **one field or vocabulary shared across several types** (a CPU shape reused by VM and BareMetal)
  — that is a `SharedDataElement` on a Class. Follow [`scoped-class.md`](scoped-class.md).
- It is **a governed list of values** (storage tiers, OS images) — that is reference data. Follow
  `reference-data.md`.
- It is **computed, negotiated, or executed** at request time — that belongs to DCM, not the data model
  (the ADR-008 peer test: portable data → UDLM; a decision → DCM).

## 2. The steps, in order

Each step names the file you touch and the artifact it produces. Copy the worked example
(`registry/resource-types/storage/storage.pool.yaml`) alongside these.

1. **Draft the spec skeleton.** Create `registry/resource-types/<domain>/<Type>.yaml`. Fill the required
   header (`$id`, `conforms_to`, `uuid` — mint a fresh UUIDv4, `resource_type` as `Category.Type`,
   `version`, `family`, `status`, `metadata`). Write the `spec` block: `type: object`,
   `additionalProperties: false` (mandatory — strict-by-default, so a misspelled field fails rather than
   silently dropping intent), the `properties`, and `required`. **Produces:** a schema-valid spec shell.
2. **Declare typed `outputs`.** Name every value the type publishes when it reaches Realized — these are
   the binding surface other types reference. A realizable type with zero outputs must instead carry an
   explicit `outputs-exempt:` note in its description saying why (rule-36 G1). **Produces:** the Realized
   contract.
3. **Write the `context` block** (`purpose`, `plain_description`, `use_when`, and the near-misses in
   `not_for`). This is the plain-English on-ramp a new engineer reads first; it renders into
   `registry/TYPE-CATALOG.md` and is required by rule-36 G7. **Produces:** the human gloss.
4. **Add `adopts[]`** for every external standard you lean on (Redfish, SNIA Swordfish, OpenZFS…). You
   reference the vocabulary by identity + version pin + recorded license verdict — never restate the
   standard's schema (core-tenet T5: adopt, don't absorb). If your prose claims an adoption, `adopts[]`
   must carry it (rule-36 G5). **Produces:** version-pinned standards references.
5. **Add `spec.examples`** — at least one worked instance inside the `spec` schema itself (ADR-055:
   examples live in the spec, the JSON Schema convention). It must validate against the very schema it
   sits in. **Produces:** the example leg of coverage.
6. **Author 2–3 Use Cases** under `use-cases/<domain>/`, each a positive, a **must-reject** (the refusal
   contract — what the type must refuse and how it names the cause), and optionally a composite. Give
   each a `handle` (e.g. `storage/provision-volume-bound-to-pool`) and fill the required `dimensions`.
   **Produces:** the corpus that exercises the type.
7. **Author or point a flow** in `docs/flows/` — the lifecycle doc that places the type in an implementation
   story. A new type in an existing family usually *points at* an existing flow rather than writing one.
   **Produces:** the flow leg of coverage.
8. **Add the `coverage:` block** to the spec, naming `use_cases:` and `flows:`. `examples` is optional
   here — `spec.examples` (step 5) satisfies the example leg. **Produces:** the structural link that
   makes the type "travel with its story."

**The lighter path for OBSERVED types.** A type populated *from* the estate rather than requested
(`Hardware.*`, `Facility.*`, `Identity.*`, `Network.Switch`/`VLAN`, `Topology`) has a lighter coverage
contract: instead of bespoke per-type UCs, point `coverage.use_cases` at the shared observation UC
`observed/estate-resource-observed` (and the quarantine must-reject
`observed/observation-off-vocabulary-quarantined`), and `coverage.flows` at
`docs/flows/estate-observation-lifecycle.md` — the flow that settles observe → normalize →
quarantine-or-graph. Read `use-cases/observed/` and that flow before authoring an observed type; you
inherit their story rather than writing your own.

## 3. Completeness checklist — and the gate that enforces each

| Ships with the type | Enforced by |
|---|---|
| Validates against `resource-type-spec.schema.json` | `registry/tools/validate.py`, `tests/validate_registry.py` |
| At least one `spec.examples` that validates against its own `spec` | `tests/check_spec_examples.py` — **EXG-002** (no example) / **EXG-001** (example that doesn't validate) |
| A `coverage:` block whose every UC handle and flow file resolves | `registry/tools/spec_coverage.py --check` — **COV-001** (dangling referent), **COV-002** (a new uncovered spec must join the backlog, not slip in) |
| A schema that is satisfiable *and* discriminating (rejects a dropped-required, a bad enum, a wrong type, an unknown key) | `registry/tools/fuzz_type_specs.py` (synthesizes instances — no fixtures) |
| `outputs` (or an `outputs-exempt:` note), a `context` block, resolvable relationship targets, `adopts[]` backing any adoption prose | `tests/check_type_standard.py` — rule-36 gates **G1** outputs, **G2** target-exists, **G5** adopts-parity, **G7** context-present |

## 4. A worked pointer

Copy **`registry/resource-types/storage/storage.pool.yaml`** — a host-local storage pool. It carries
every part in one file: the `spec` with a recursive `$defs.vdev` tree, typed `outputs`
(`usable_capacity`, `fault_tolerance_remaining`…), `adopts[]` for OpenZFS + SNIA Swordfish, an in-spec
`spec.examples`, a full `context` block, and a `coverage:` block. For the UC pair to model, copy
`use-cases/storage/001-provision-volume-bound-to-pool.yaml` (positive) and
`use-cases/storage/002-volume-request-exceeds-quota-refused.yaml` (the must-reject, whose success *is*
the refusal). For the flow,
see `docs/flows/storage-provisioning-lifecycle.md` — how pool → dataset → volume composes into one
implementation.

## 5. Run the gates

From the repo root:

```
python3 tests/check_spec_examples.py
python3 registry/tools/spec_coverage.py --check
python3 registry/tools/fuzz_type_specs.py
python3 tests/check_type_standard.py
```

A pass looks like:

- **check_spec_examples.py** — `NN/NN resource-type spec(s) carry a validated example; …` and exit 0
  (no `FAIL [EXG-…` lines).
- **spec_coverage.py --check** — your type shows `✓ UC+example+flow`, the run ends `… covered · … in
  backlog · 0 dangling`, and exit 0 (no `FAIL [COV-…`). If your type is new and *un*covered, expect
  COV-002 to grow the backlog file — commit that change.
- **fuzz_type_specs.py** — `OK — every spec is satisfiable and discriminating` and exit 0.
- **check_type_standard.py** — `N violation(s): N baselined, 0 NEW; …` with **0 NEW** and exit 0. A new
  violation (not in the burn-down baseline) fails; never grow the baseline to hide it.

`./scripts/signoff.sh` runs these alongside the whole gate set before you open a PR.

# Authoring a process

**What this gets you.** A process — a job or operation with a blast-radius — modeled so that what it needs
stays up while it runs, what it may touch is declared, and the engine that runs it is a swappable provider
detail. UDLM gives you **two shapes** for a process; this doc tells you which to reach for and how to
author each so CI accepts it.

A process is the Process family (`family: Process`): a bounded execution, not a maintained state. The two
shapes are:

- **A Process-family Class** (`registry/classes/automation*.yaml`, validated against
  `registry/class.schema.json`) — the portable, multi-engine definition. Use it when the *point* is that
  more than one engine can honor the same process, so migration between engines is a provider swap.
- **The `Automation.Job` resource type** (`registry/classes/job.yaml`,
  validated against `registry/resource-type-spec.schema.json`) — a job as a first-class node in the
  dependency graph. Use it when you need the job's dependencies and blast-radius as data, without the
  full multi-provider Class apparatus.

Read both schemas and both worked examples before choosing.

## 1. When to use it — which shape, and when neither

**Author a Process-family Class** when the recurring problem is **platform-to-platform automation
migration**: two engines (blue today, green tomorrow) must run *the same* OS-patch or backup definition,
org policy gates the portable definition, and lock-in should be readable as exactly the elements sitting
at engine scope. This is the shape the implementation-plan flags as most-used — resource-provider migration
is episodic, automation-engine migration is recurring.

**Author an `Automation.Job` resource type** when you need **a job as a graph node with real
dependencies** — its executor host, the fabric it traverses, the name service it resolves through — so an
ordered operation (a UPS-triggered graceful shutdown, a rolling upgrade) falls out of the reverse-topological
sort with no hand-written runbook, and so a resource can cite the job that changed it in its provenance.
It carries the automation intent (`definition_ref`, `parameters`, `targets`, `schedule`) portably, but
does not itself model multiple engines competing on one definition.

Do **not** author a process when:

- The thing is **a maintained state**, not a bounded execution (a Service the job *deploys*, a Container
  the job *runs in*) — that is a resource type. Follow [`resource-type.md`](resource-type.md). A process
  must declare a bound on its execution time; a service has no scheduled end.
- The behavior is **computed or executed** rather than declared — the run engine, the placement, the
  give-up window are DCM's, not the data model's (the ADR-008 peer test).

## 2. The steps, in order

### Shape A — a Process-family Class

Follow [`scoped-class.md`](scoped-class.md) for the full Class procedure; the Process-specific parts:

1. **Author the Base and Type Classes.** The Process Base Class carries what every run shares —
   `inputs_schema`, `outputs_schema`, `idempotency` (`idempotent` / `at-most-once` / `unsafe-repeat` —
   the re-run semantics), `timeout`, `retry_policy`, `compensation`, and **`affected_entities`** (the
   blast-radius declaration — which records this run may mutate). Your Type Class (`Automation.OSPatch`)
   extends it with the domain intent (`targets`, `patch_policy`, `reboot_policy`) under Liskov.
   **Produces:** `registry/classes/automation.yaml` + `registry/classes/automation.ospatch.yaml`.
2. **Author a Provider Class per engine.** Each engine (`Automation.OSPatch.EngineBlue`,
   `…EngineGreen`) adds only its engine-native elements (`definition_ref`, `control_server`,
   `start_jitter`) — never contradicting the portable Type. **Two engines declaring the same Type Class
   is the multi-provider declaration**: engine migration becomes a provider swap on an untouched
   `Automation.OSPatch`. **Produces:** the provider-tier bindings; the lock-in surface, made readable.
3. **Compile and cover.** Run the generator, commit `registry/generated/automation.ospatch.json`, and add a
   `coverage:` block. Point it at the process/migration corpus below.

### Shape B — an `Automation.Job` resource type

Follow [`resource-type.md`](resource-type.md); the process-specific parts:

1. **Declare the mandatory execution bound.** `process_type` and **`max_execution_time`** (ISO-8601
   duration) are required — a job that never declares when it must stop is not a job. Add `on_max_exceeded`
   and `trigger` (`manual` / `event` / `schedule`).
2. **Carry the automation intent portably.** `definition_ref` (a typed reference or a version-pinned
   `automation_definition` data_reference — never an inline body or a provider-native id), `parameters`
   (opaque to the substrate, validated by the provider at naturalization), `targets` (typed resource
   References by `target_handle`), and `schedule` (`expression`, `overlap_policy`, `missed_run_policy`).
   Because the intent lives on the record, moving to a different engine is a provider change on an
   untouched definition.
3. **Declare the blast-radius, and the outputs stance.** `depends_on` edges are the executor host, fabric,
   and resolver — a running job pins them (orchestrator stops last). The `affected_entities` edge is
   informational (§6.4 makes the *affected* entity cite the job's uuid). Every run-history fact is an
   output of a *run instance*, not of the job — so `Automation.Job` carries `outputs: {}` plus an explicit
   `outputs-exempt: run-scoped` note (rule-36 G1 is satisfied by the note, not by empty outputs).

## 3. Completeness checklist — and the gate that enforces each

**Shape A (Process-family Class):**

| Ships with it | Enforced by |
|---|---|
| Validates against `class.schema.json`; every redeclare refines its parent | `tests/check_class_liskov.py` — **LSK-001** |
| Type Class compiles to a conformant flat spec, committed and fresh | `registry/tools/generate_class_specs.py --check` — **GEN-001/002** |
| `coverage:` block resolves | `registry/tools/spec_coverage.py --check` — **COV-001** |

**Shape B (`Automation.Job` resource type):**

| Ships with it | Enforced by |
|---|---|
| At least one validating `spec.examples` | `tests/check_spec_examples.py` — **EXG-001/002** |
| Satisfiable and discriminating schema | `registry/tools/fuzz_type_specs.py` |
| `outputs` **or** an `outputs-exempt:` note, a `context` block, resolvable relationship targets, `adopts[]` backing adoption prose | `tests/check_type_standard.py` — rule-36 **G1/G2/G5/G7** |
| `coverage:` block resolves (or the spec visibly joins the backlog) | `registry/tools/spec_coverage.py --check` — **COV-001/002** |

> **On the backlog grace:** `spec_coverage` COV-002 permits a spec to sit in
> `registry/spec-coverage-backlog.yaml` (the shrinking backfill list) *only* as long as the backlog file
> stays in sync — this is how a large migration burns down without blocking. The tree is now fully covered
> (backlog empty), so a *new* process you author gets no grace: declare a `coverage:` block, or CI refuses it.

## 4. A worked pointer

- **Process-family Class:** copy `registry/classes/automation.yaml` (Base — note the `affected_entities`
  blast-radius element and the `idempotency` codelist), `registry/classes/automation.ospatch.yaml` (Type),
  and `registry/classes/automation.ospatch.engine-blue.yaml` + `…engine-green.yaml` (the two Provider Classes
  that make migration a provider swap).
- **`Automation.Job` resource type:** copy `registry/classes/job.yaml` — the
  first Process-family resource type, with `depends_on` graph edges, the portable-intent block
  (`definition_ref` / `parameters` / `targets` / `schedule`), the `outputs-exempt` stance, its
  `spec.examples`, and its `coverage:` block naming `use-cases/automation/run-automation-job.yaml`
  (idempotent run with a declared blast-radius) and `docs/flows/automation-migration-and-promotion.md`.
- **Corpus and flow:** `use-cases/process-migration/` (`automation-staged-promotion`,
  `blue-green-engine-verification`, `engine-migration-canary-cutover`, `engine-upgrade-regression`,
  `process-portability-structural-query`) and `docs/flows/automation-migration-and-promotion.md` — how
  automation moves between engines, engine versions, and environments using only placement machinery, with
  verification as an empty output-diff. (The worked `Automation.OSPatch` pilot pair currently declares its
  coverage against the `scoped-class/*` corpus and `docs/flows/scoped-class-lifecycle.md`, because it is
  also the Class-system pilot; a production process should point at the process-migration corpus above.)

## 5. Run the gates

**Shape A — a Process-family Class:**

```
python3 tests/check_class_liskov.py
python3 registry/tools/generate_class_specs.py --check
python3 registry/tools/spec_coverage.py --check
```

Pass: `N class(es) checked, 0 Liskov violation(s)`; a `ok (fresh)  Automation.OSPatch → registry/generated/automation.ospatch.json (N props)`
line ending `N Type Class(es) compiled, 0 issue(s)`; and `… 0 dangling` — each exit 0.

**Shape B — an `Automation.Job` resource type:**

```
python3 tests/check_spec_examples.py
python3 registry/tools/fuzz_type_specs.py
python3 tests/check_type_standard.py
python3 registry/tools/spec_coverage.py --check
```

Pass: `… carry a validated example` (no `FAIL [EXG-…`); `OK — every spec is satisfiable and
discriminating`; `N violation(s): … 0 NEW`; and `… 0 dangling` — each exit 0.

`./scripts/signoff.sh` runs both sets with the full gate suite before you open a PR.

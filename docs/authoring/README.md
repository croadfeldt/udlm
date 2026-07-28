# Authoring UDLM artifacts — start here

> Part of **[Working with UDLM](../working-with-udlm.md)** — the author track. Reviewing instead?
> [reviewing.md](../reviewing.md). Building a system on the model? [consuming.md](../consuming.md).
> New contributor? [contributing-guide.md](../contributing-guide.md).

**What this is.** The replicable procedure for adding anything to the UDLM registry: a resource type, a
Class, a process, a policy, a provider/API, reference data, or a corpus artifact (Use Case, flow, ADR).
Written so someone who wasn't here can add an artifact correctly and have CI accept it. If you follow the
HOWTO for your artifact kind, the gates will pass; if you skip a step, a gate will name it.

> **Read once, first:** [`CONTRIBUTING.md`](../../CONTRIBUTING.md) — subject-scoped PRs, the DOC-001
> writing standard, and the review sweep. This guide is the *procedure*; CONTRIBUTING is the *standards*
> the procedure satisfies.

## The universal contract — every artifact

Whatever you author, four things must be true before it merges. The gate that enforces each is named so
you can run it yourself (all run in `.github/workflows/validate.yml`; `./scripts/signoff.sh` runs the set).

1. **Valid by construction** — it validates against its schema in `registry/*.schema.json`.
   *Gate:* `tests/validate_registry.py`, `registry/tools/validate.py`.
2. **Identity is honest** — a new artifact mints a fresh `uuid`; a change to a published one bumps its
   `version` (never edits in place for immutable records). *Gate:* `tests/check_identity_integrity.py`
   (ADR-051).
3. **It travels with its story** — a resource type / Class ships a **Use Case + in-spec example + flow**,
   declared in a `coverage:` block. *Gates:* `registry/tools/spec_coverage.py` (COV-001/002),
   `tests/check_spec_examples.py` (EXG-001/002). (rule-36; ADR-055.)
4. **It reduces to existing where it can** — before coining a new mechanism, show no existing one
   (classification, profiles, references, edges, a Class) composes to cover it. *Check:* review sweep
   tenet T7.

## Pick your artifact kind

| You are adding… | Follow | Its schema | Its completeness gate(s) |
|---|---|---|---|
| A **resource type** (VM, Volume, Service, DNSZone…) | [`resource-type.md`](resource-type.md) | `resource-type-spec.schema.json` | EXG-001/002, COV-001/002, fuzz, rule-36 |
| A **Class** (Base/Type/Provider scoped-Class) | [`scoped-class.md`](scoped-class.md) | `class.schema.json` | Liskov, generate_class_specs, COV |
| A **process** (a job/operation with blast-radius) | [`process.md`](process.md) | `class.schema.json` (Process family) / `resource-type-spec` (Automation.Job) | as Class / resource type |
| A **policy** (schedule, validation, override…) | [`policy.md`](policy.md) | `policy.schema.json` | validate, rule-IDs, terminology |
| A **provider / API** (a naturalizing backend) | [`provider-api.md`](provider-api.md) | `provider-adopted-standards.schema.json`, `function-capability-matrix.schema.json` | provider-contracts, standards-registered |
| **Reference data** (a governed vocabulary) | [`reference-data.md`](reference-data.md) | `layer.schema.json` (`reference_data_type`) | validate, single-source |
| A **Use Case** (corpus scenario) | [`use-case.md`](use-case.md) | dcm engine UC schema | DIM-001, personas |
| A **flow** (a lifecycle doc) | [`flow.md`](flow.md) | — (Markdown convention) | links, coverage-referent |
| An **ADR** (a decision record) | [`adr.md`](adr.md) | `decision-record.schema.json` | terminology, single-source, DOC-001 |

## The shape of every HOWTO

Each linked HOWTO follows the same spine, so the procedure is uniform across kinds:

1. **When to use it** (and when *not* to — the near-miss that belongs to another kind).
2. **The steps**, in order, each naming the file you touch and the artifact you produce.
3. **The completeness checklist** — what must ship with it, and the gate that enforces each item.
4. **A worked pointer** — an existing artifact of this kind to copy.
5. **Run the gates** — the exact command, and what a pass looks like.

## The one rule behind all of it

*Write for a reader who wasn't there* (DOC-001). Every artifact — spec, example, UC, flow, ADR — is read
by someone without your context. The gates verify structure; only you can make it *legible*. The accuracy
sweep (`spec_coverage` COV-004) checks that a spec's declared UCs/examples/flows actually reference it, and
the DAV analysis measures whether the corpus is semantically coherent against the model — but neither
writes the clear sentence. That's the author's job, every time.

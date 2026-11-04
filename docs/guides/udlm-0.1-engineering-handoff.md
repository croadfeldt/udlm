# Engineering handoff

For the team that will build on UDLM. One page: where to start, what the model is, where the
truth lives, what is experimental, what is known to be open, and how to check your work. It points
at the normative documents and does not restate them.

## 1. Where to start

| You are | Open |
|---|---|
| new to the model | [`docs/start-here/`](../start-here/README.md), eleven short steps, each ending with a command that proves it |
| in a hurry | [`quickstart.md`](quickstart.md), one VM through its four records in ten minutes |
| about to write something | the "copy this file" table in [`co-engineering.md`](co-engineering.md): a record, a Provider Class, a layer |
| building a control plane, a provider or a tool | [`consuming.md`](consuming.md) |
| joining from another organization | [`co-engineering.md`](co-engineering.md): how to check your records, change the spec, and how decisions are made |

## 2. The model in one page

- **A thing has one identity for life** (`entity_uuid`), and four records about it: what was
  intended, requested, realized and discovered. One record per state, written by a different
  author each. A record is never edited; a change is a new record that supersedes the old one.
  [`four-states.md`](../spec/foundations/four-states.md).
- **A class says the shape**, in three tiers: a Base (`Machine`), a Type (`Machine.VM`), and a
  Provider Class (`Machine.VM.CExampleCloud`) that narrows what the parent allows and adds what only
  that provider needs. A child refines its parent and never contradicts it; a gate checks that. The
  served spec under `registry/generated/` is what a record's `type_ref` points at.
  [`class-tiers.md`](../spec/foundations/class-tiers.md).
- **Edges are the graph.** Four edge types (`depends_on`, `contained_by`, `binds_to`,
  `references`) on the record; no bundle or stack objects. A cross-tenant edge names the owning
  tenant and the authorization it relies on.
  [`entity-relationships.md`](../spec/foundations/entity-relationships.md).
- **Layers fill and bound a request** before a provider sees it, lowest authority first, with
  per-field provenance; a layer's bounds can only tighten down the chain. UDLM ships no defaults;
  the values an estate wants live in the estate's own layers.
  [`layering-and-versioning.md`](../spec/foundations/layering-and-versioning.md).
- **Policy is separate from data.** Layers carry values; policies decide. The rule body is opaque
  to the model; what the model fixes is the facts a policy may read and the outcomes it may return.
  [`policy-contract.md`](../spec/contracts/policy-contract.md).
- **A provider registers what it offers** and reports back what it built, in the record's
  `outputs`. [`provider-contract.md`](../spec/contracts/provider-contract.md) (7f's section below).
- **Conformance is record level.** An implementation claims UDLM by the records it writes, judged
  by the suite. [`CONFORMANCE.md`](../../CONFORMANCE.md).

## 3. Where the truth lives

The spec is the source of truth; every derived file is regenerated from it and gated for freshness.

- **Record schemas** `registry/*.schema.json`: `state-record` (the four states), `entity-view` (the
  read model, never written), `layer`, `policy`, `profile`, `composition`, `provider-registration`,
  `provider-adopted-standards`, `accreditation`, `audit-record` with `audit-leaf` and
  `commit-log-entry`, `decision-record`, `regeneration-manifest`, `finding-routing-record`,
  `conformance-declaration`, `vocabulary-term`, `data-reference`, `evaluation-context`,
  `function-capability-matrix`. `common-elements.schema.json` holds the shared definitions.
- **Classes** `registry/classes/<family>/<group>/...`, one file each; the served specs under
  `registry/generated/`; the catalog `registry/TYPE-CATALOG.md`.
- **Contracts** `docs/spec/contracts/`, **foundations** `docs/spec/foundations/`, **governance**
  `docs/spec/governance/`, **lifecycle** `docs/spec/lifecycle/`, **principles** `docs/spec/principles/`.
- **Decisions** [`docs/adr/README.md`](../adr/README.md): every ruling is a dated row, newest on
  top. When you wonder why, the answer is a row.
- **Versions** [`registry/VERSIONING.md`](../../registry/VERSIONING.md): the spec and each class
  have their own version, and a record pins both. Before 1.0 a breaking change is a minor bump.

## 4. What is experimental

Everything. [`registry/stability.yaml`](../../registry/stability.yaml) has a row for every class,
schema and document: 153 are `experimental`, 7 are `reference` (documents that state no rule), none
is `candidate` or `stable`. That is by ruling, not neglect: a part earns a stage by being used and
validated, and your implementation is how it gets there. The ladder is
[`graduation.md`](../spec/governance/graduation.md). Candidate needs a worked record, a must-reject
case per rule and readable text. Stable needs 90 days as a candidate and a conformance report from
a running implementation that judged at least ten of its records.

What that means for you: pin the spec version and each class version you build against, and move
the pins on purpose. Within 0.x a minor version may change a part you use. The 1.0 tag covers
whatever is stable when the maintainer calls it; the road there is
[`UDLM-1.0-LOCKDOWN.md`](../../registry/UDLM-1.0-LOCKDOWN.md).

## 5. Known open

Nothing here blocks building; each is a place where you may hit an edge and should know it is known.

- **Rulings in flight.** #723 settled eight places where a schema and the spec disagreed: policy
  statuses and operations, layer precedence, group membership, the policy trigger for relationship
  events. The PRs that apply them follow. #724: rule ids cited with no definition. #725: two
  decision records point at a renamed schema file. #726: small leftovers from the documentation sweep.
- **Coverage backlog.** 59 of 71 classes have no `coverage:` block yet; the gate was silent until
  #722. The backlog is `registry/spec-coverage-backlog.yaml` and it only shrinks.
- **Layers are designed, not exercised.** Seven layer types, precedence, bounds and lineage are
  specified and gated, and no assembly run has used them. Yours would be the first.
- **Profiles are mechanism only.** The six postures live in a separate repository; this one says
  what a profile is, not which one you should run.
- **Earlier items** are open issues on the repository; none is a defect in what ships.

## 6. How to check your work

```bash
python3 registry/tools/validate.py     # every record and class validates; what fails says why
./scripts/signoff.sh                   # every CI gate, about three minutes; run before a PR
./scripts/signoff.sh --only 'Liskov'   # a named subset while you work
./scripts/regen.sh                     # after a class change: regenerate every derived file
```

The gates check this repository. The conformance suite checks you; the next section says how.

## 7. The provider contract

<!-- 7f writes this: what a provider registers, what it must honor, where the schema-checked examples are -->

## 8. The conformance suite and your evidence

<!-- 7f writes this: running the suite on your records, keeping the report, what it proves and what it does not (pinned class versions) -->

## 9. Estate evidence

<!-- 7f writes this: the estate CI job that keeps a conformance report from every run, as the evidence promotions cite -->

## 10. Changing the spec, and where to ask

Open an issue that says what breaks and which record shows it. A pull request changes `docs/spec`
first and every derived file in the same change, carries a register row, and passes every gate.
Plain English is a rule here: a reader who was not in the room understands a row or a description
cold. Decisions are made in the open, as register rows, by the maintainers in `MAINTAINERS.md`.
There is no private channel.

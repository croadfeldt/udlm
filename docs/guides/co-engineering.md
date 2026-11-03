# Co-engineering with UDLM — the front door

For an engineer joining from another organization. One page: what this is, what to read, how to
check your own records, how to change the spec, and how decisions are made.

## What this is

UDLM is a data model for infrastructure: classes that say what a thing is, records that say what
was intended, requested, realized and discovered about it, and the rules that bind them. It is a
specification with a conformance suite, not a product. An implementation that passes the suite
is a peer of every other.

## Read, in this order

1. [`README.md`](../../README.md) — the on-ramp and the repository layout.
2. [`registry/UDLM-1.0-LOCKDOWN.md`](../../registry/UDLM-1.0-LOCKDOWN.md) — where the spec is
   on its way to 1.0: what 1.0 will promise, what is frozen, and what waits.
3. [`docs/spec/foundations/data-model-core.md`](../spec/foundations/data-model-core.md) and
   [`docs/spec/foundations/class-tiers.md`](../spec/foundations/class-tiers.md) — the records and
   the classes.
4. [`docs/spec/governance/graduation.md`](../spec/governance/graduation.md) — how a part earns
   stability. Everything is experimental until it has been used and validated; your implementation
   is how parts get there.
5. [`registry/VERSIONING.md`](../../registry/VERSIONING.md) and [`CONFORMANCE.md`](../../CONFORMANCE.md)
   — what a version means and what conformance certifies.
6. [`docs/adr/README.md`](../adr/README.md) — the decisions register. Every ruling is a dated row,
   newest on top. If you wonder why something is the way it is, the answer is a row.

## Check your own records

The conformance suite judges a tree of state records against the registry:

```bash
python3 tests/conformance.py path/to/your/records --report conformance-report.json
```

Exit 0 means every rule held. The report names the suite version, the UDLM commit, and the
classes it judged with a count per class. Keep the report: it is the evidence a part needs to be
promoted ([`graduation.md`](../spec/governance/graduation.md) §2), and it is what your conformance
declaration cites. Pin the UDLM commit you validate against; move the pin on purpose.

## Change the spec

- **Something is wrong or missing in a part you use.** Open an issue that says what breaks and
  which record shows it. If the fix would be a breaking change after 1.0 — a rename, a removed or
  narrowed field, a closed list that is not settled — it is a 1.0 blocker and goes first.
- **Something new** — a class, an optional field, an output, an edge — is additive. Open the issue
  with the `1.x` label, or a draft pull request that says it waits on the freeze
  ([lockdown plan §3](../../registry/UDLM-1.0-LOCKDOWN.md)). The maintainer rules on it.
- **A pull request** changes `docs/spec` first and every derived file in the same change, carries
  a register row, and passes every step in `.github/workflows/validate.yml`. Run them all before
  you push; the readability gate will ask for short sentences, and the estate-token guard will
  refuse private hostnames and addresses — use RFC 5737 ranges in examples.
- **Plain English** is a rule here, not a preference: a reader who was not in the room understands
  a row, a rule or a description cold.

## How decisions are made

By the maintainers listed in the maintainers file at the repository root, in the open, as register
rows. A ruling you disagree with gets an issue, not a silent edit. Becoming a maintainer is a row
too, after three months of reviewed contributions.

## Where to ask

Issues on this repository. There is no private channel for decisions.

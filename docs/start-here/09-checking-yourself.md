# Step 9 — checking yourself

The gates check this repository. The conformance suite checks you: the records your own system
writes, against the rules the spec states. Passing it is what "implements UDLM" means.

## Do this

1. Run the suite on itself:

```bash
python3 tests/conformance.py --self-test
```

   It reports the worked records that pass, the must-reject cases that are refused for the right
   rule, and that every rule is covered. A rule with no must-reject case is a rule nobody has
   shown can fail; the suite does not allow one.
2. Run it on a tree of records and keep the report:

```bash
python3 tests/conformance.py registry/examples --report conformance-report.json
```

   Exit 0 means every rule held. Open the report: it names the suite version, the UDLM commit it
   judged against, the records, and a count per check. For your own system the path is wherever it
   writes records.
3. Open [`registry/stability.yaml`](../../registry/stability.yaml). Every part of the spec has a
   stage, and today every one is `experimental`. Nothing is stable because nothing has been used
   and validated yet.

## Why the report matters

A part of the spec moves up a stage by evidence, not by declaration. The ladder is three steps:

- **experimental**: written, with a worked example.
- **candidate**: a worked record, a must-reject case per rule, readable text, no open blocker.
- **stable**: 90 days as a candidate with no breaking change, and a conformance report from a
  running implementation that judged at least ten of its records.

That report is the one you just made. An implementation that keeps its reports is how UDLM earns
"stable", part by part, and the 1.0 tag covers whatever is stable when the maintainer calls it.
The rules are in [`docs/spec/governance/graduation.md`](../spec/governance/graduation.md).

## Done when

You have a `conformance-report.json`, can say which commit it judged against, and can say what a
part needs to go from candidate to stable.

Next: [Step 10 — where next](10-where-next.md).

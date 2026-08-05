# Authoring a flow

A flow is a **lifecycle doc** in `docs/flows/` — a Markdown narrative of how a family of resources
moves from intent to realized (or to a bounded refusal), with the failure branches drawn inline. It is
the third leg of a type's story: **Use Case + in-spec example + flow**, declared in the type's
`coverage:` block. This HOWTO is the convention; there is no schema, so the discipline *is* the
template.

> **Read once, first:** [`README.md`](README.md) (the universal contract) and the two exemplars this
> guide points at.

## 1. When to use it — and when not

Author a flow when a capability spans **more than one type or more than one step** and the ordering,
the branch points, and the refusal paths are the thing worth documenting — how a pool, a dataset, and
a share compose into one implementation; how an observed resource is normalized or quarantined.

Do **not** reach here for:

- a single type's **behavioral assertion** — that is a Use Case ([`use-case.md`](use-case.md));
- a single type's **worked instance** — that is `spec.examples` in the spec;
- a **decision** about why the model is shaped this way — that is an ADR ([`adr.md`](adr.md)).

A flow **builds on** [`../flows/request-realization.md`](../flows/request-realization.md) (the base
intent→realized loop every family shares) and documents only what *your* family adds. If your doc
restates the base loop, it is too heavy — cut back to the delta.

## 2. The steps, in order

1. **Create** `docs/flows/<family>-<lifecycle>.md` (e.g. `storage-provisioning-lifecycle.md`).
2. **Write the spine**, in this order — the exemplars are byte-for-byte templates:
   - **`# Title`** naming the family and the arc.
   - **`**What this settles:**`** — one thesis paragraph. Say what the flow resolves and that it is a
     *lighter* doc building on `request-realization.md`, so a reader knows its scope.
   - **A `>` blockquote** listing the **Use Cases** (positive and must-reject, by handle), the
     **Persona(s)**, and — because a flow is a coverage referent — the **resource types / family** it
     covers. This line is what ties the flow back to the specs that name it.
   - **`**In one breath.**`** — the whole lifecycle in one dense paragraph.
   - **`## The flow`** — a **mermaid `flowchart`** with the failure and refuse branches drawn *inline*
     (not a separate diagram): every `{decision}` node has its `-->|no|` refusal edge naming the root
     cause, not just its happy edge.
   - **`## What <the delta> adds`** — bullets for what this family adds over the base loop.
   - **`## What UDLM does not decide`** — the DCM boundary (ADR-008): which provider backs it, how it
     naturalizes, where the give-up bound lives. This section keeps the flow on the data-model side.
   - **`## Where each piece is specified`** — a pointer table: each piece → its contract (an ADR, a
     spec path, the corpus directory). References carry their gist, never a bare number.
3. **Wire the flow into `coverage:`.** In each spec whose story the flow completes, add the flow's
   path under `coverage.flows:` (see `registry/classes/resource/storage/pool.yaml` — its
   `coverage.flows` lists `docs/flows/storage-provisioning-lifecycle.md`). A flow no spec references is
   an orphan.

## 3. The completeness checklist — and the gate for each

A flow carries **no schema gate** — its correctness is link-integrity plus being a resolvable coverage
referent.

| Ships with the flow | Enforced by |
|---|---|
| Every relative Markdown link resolves | `tests/check_links.py` — a broken relative link fails CI |
| The flow path under a spec's `coverage.flows:` resolves to this file | `registry/tools/spec_coverage.py` (COV) — a coverage referent that does not resolve fails |
| No retired terminology in the prose | `tests/check_terminology.py` — TERM-001 |
| No estate tokens (personal host/site names, estate IPs) | `tests/check_estate_tokens.py` |
| The blockquote names the resource type / family, so the flow is discoverable from its specs | convention (the spine) |

Because there is no structural gate, the spine *is* the contract: a reader who wasn't there gets the
thesis, the one-breath summary, the branched diagram, the boundary, and the pointer table — or the
flow has not done its job.

## 4. A worked pointer

Copy the closest of these two:

- A **provisioning** family (compose several types into one ordered implementation):
  [`../flows/storage-provisioning-lifecycle.md`](../flows/storage-provisioning-lifecycle.md) — pool →
  dataset → volume/share, three refusals with three roots drawn inline, builds on
  `request-realization.md` and `uc-06-persistent-volume-provision.md`.
- An **observation** family (resources discovered rather than requested):
  [`../flows/estate-observation-lifecycle.md`](../flows/estate-observation-lifecycle.md) — observe →
  normalize → quarantine-or-graph, with the refusal→audit-record cross-cut stated once and referenced,
  not restated per type.

## 5. Run the gates

```console
$ python3 tests/check_links.py
232 files scanned, 0 broken link(s)
```

The pass signal is the trailing `0 broken link(s)`. To confirm the flow is a resolvable coverage
referent, run the coverage gate over the spec that names it (`python3 registry/tools/spec_coverage.py`);
both run in `./scripts/signoff.sh` with the full set.

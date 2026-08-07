# The 21 release use cases vs the corpus — reconciliation

**What this settles:** which of the 21 release-scope use cases (`registry/UDLM-0.1-SCOPE.md`) already
exist in the `use-cases/` corpus under a different handle, and which are genuinely absent. The corpus
is the broader register (149 entries) and **should contain the 21**; today **none of the 21 resolve**.

**Why it matters now:** every `uc-NN-*.md` flow ends with `UC source: <handle>`, and all 23 of those
pointers dangle. An engineer reading a flow and wanting the authoritative scenario — success criteria,
actors, refusal cases — has nowhere to go. The pointer is the one line that makes a flow traceable.

Nothing validates any of this: `check_uc_dimensions` and `check_uc_personas` gate the corpus's internal
vocabularies, but no gate connects flow → scope → corpus.

---

## A — Rename: the corpus entry exists, the handles disagree

The scenario is the same; one of the two names is wrong. Cheapest to close, and closing it is a naming
decision, not authoring work.

| UC | Scope handle | Corpus handle | Note |
|---|---|---|---|
| 03 | `compute/vm-standard-provision` | `compute/provision-vm-standard` | Same words, reordered. Unambiguous. |
| 11 | `compute/vm-provision-with-provider-failure` | `compute/vm-provision-provider-failure-refused` | Corpus adds the `-refused` suffix its must-reject convention uses. |
| 06 | `data/persistent-volume-provision` | `storage/provision-volume-bound-to-pool` | Same scenario; corpus namespace is `storage/`, not `data/`, and names the pool binding. |
| 02 | `cross-domain/solution-architecture-deployment` | `architecture/solution-architecture-decomposition` | Same actor and output. *Deployment* vs *decomposition* is a real difference in emphasis — confirm the corpus entry covers the deploy leg, not just the decompose leg. |

## B — Absent: no corpus entry covers this scenario

These need authoring. Checked against the full 149 — the near-miss column names the closest entry and
why it is **not** the same use case.

| UC | Scope handle | Closest corpus entry | Why it does not cover it |
|---|---|---|---|
| 04 | `compute/vm-intent-osac-placement` | `osac/provider-portability-new-cloud` | The `osac/` set covers registration, capacity advertisement, rehydration, and portability. None is *a VM intent placed onto OSAC and realized with OSAC provenance* — which is the whole point of UC-04. |
| 12 | `…/rehydration-rto-measurement` | — | Nothing in the corpus measures rehydration time-to-restore. Zero keyword candidates. |
| 20 | `cross-domain/profile-resolution-capability` | — | Zero candidates. Profiles are exercised as a *dimension* across the corpus, never as a resolution use case. |
| 14 | `…/drift-detection-remediation` | `bare-metal/host-rehydration-replay-intent` | Rehydration replays intent; it does not detect divergence and open a drift record. No drift UC exists. |
| 15 | `…/audit-merkle-tree-verification` | `audit/refusal-emits-audit-record` | That entry is the single home of "every refusal emits a record". It does not verify a Merkle tree or an inclusion proof. |
| 21 | `…/audit-chain-proofs-capability` | `audit/refusal-emits-audit-record` | Same gap as UC-15 — emission is covered, *proof* is not. |
| 13 | `compute/idempotent-reconvergence` | `process-migration/blue-green-engine-verification` | Behavioural equivalence between engines, not resubmit-and-stop-before-dispatch. |
| 19 | `…/policy-resolution-capability` | `vocabulary-intake/near-match-never-silently-bound` | Vocabulary binding, not "evaluate only the policies in the resolved profile". |
| 05 | `libvirt-vm-provider/vm-status-provenance` | `compute/provision-vm-standard` | Provisioning publishes outputs; UC-05 is specifically *field-level provenance* — who produced each realized field, in which run, when. |
| 01 | `libvirt-vm-provider/vm-resource-representation` | `compute/provision-vm-standard` | UC-01 is about the **type**: what `Compute.VM` is made of (spec, lifecycle intent, realized status). The corpus entry is a provisioning scenario that *uses* the type. Possibly better served by the `scoped-class/` set — see C. |

## C — Needs a ruling before it can be classified

| UC | Scope handle | The question |
|---|---|---|
| 07 | `dcm-core/udlm-dependency-graph-data-model` | The `intent-fulfillment/` set (9 entries) covers dependency semantics thoroughly. Is UC-07 satisfied *collectively* by that set, or does the release register need one entry asserting "the graph is modeled data, not runtime inference"? |
| 08 | `libvirt-vm-provider/cross-provider-dependency-ordering` | `intent-fulfillment/request-dependency-atomic` is close. Does it carry the *cross-provider* boundary, or only ordering within one provider? |
| 09 | `libvirt-vm-provider/dependency-failure-impact` | `intent-fulfillment/operational-dependency-cascade` and `operational-transitive-refusal` split this between them. One release UC, two corpus entries — is that a mapping or a gap? |
| 10 | `cross-domain/dynamic-rehydration` | Three rehydration entries exist (`osac/cloud-rehydration-from-intent`, `bare-metal/host-rehydration-replay-intent`, `multi-cluster/self-managed-hub-rehydration`). Is the cross-domain case the union of these, or its own scenario? |
| 16 | `…/policy-override-approval` | `change-control/expedite-break-glass` is the closest. Break-glass and policy-override-with-approval may be the same mechanism under two names. |
| 17 | `libvirt-vm-provider/provider-registration-capability` | `osac/cloud-provider-registration` covers registration + capability + capacity. Is UC-17 the generic case that entry already proves, or does a compute-provider-specific one belong alongside it? |
| 18 | `cross-domain/provider-portable-rebuild` | `osac/provider-portability-new-cloud` covers intent moving to a new cloud unchanged. Is the "rebuild onto an alternate provider after failure" leg the same UC? |

---

## Two structural problems the mapping exposes

**Three scope handles are document paths, not use cases.** UC-12, UC-14, UC-15, UC-16, UC-19, and UC-21
are spelled `docs/spec/contracts/…` and `docs/spec/governance/…` in the scope register's handle column.
A document is not a use case; those rows never had a corpus handle to dangle *from*. This is why the
`docs/spec/*` rows cluster in section B — the register recorded where the *requirement* is written, not
what the *scenario* is.

**The `libvirt-vm-provider/*` and `dcm-core/*` namespaces do not exist in the corpus at all.** Five scope
UCs use them. The corpus organizes by domain (`compute/`, `storage/`, `network/`) rather than by
provider, so those five need a namespace decision, not just a rename.

## Recommended sequence

1. **Section A first** — four rename decisions, no authoring, and it immediately makes four flows
   traceable. Decide which name wins per row; the corpus name is usually the better one (it follows the
   corpus's own conventions, and the register's is often a paraphrase).
2. **Section C rulings** — seven judgment calls, each cheap to answer and each potentially removing a
   row from section B.
3. **Section B authoring** — whatever survives. Expect fewer than ten.
4. **A gate** — once the mapping holds, `UC source:` in a flow and the handle column in the scope
   register must both resolve to a corpus handle. Without it this drifts straight back: the register and
   the corpus have already diverged completely with nothing to catch it.

## Confidence

Section A is high confidence (read both records). Section B is high confidence for 04/12/20 (checked the
full corpus by keyword and by namespace) and **medium** for the rest — I read the closest candidates, not
all 149 entries against each of the 21. Section C is explicitly unresolved. Treat B's medium rows as
"probably absent, worth one more look before authoring".

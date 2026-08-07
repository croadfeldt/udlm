# The 21 release use cases vs the corpus — reconciliation

**What this settles:** which of the 21 release-scope use cases (`registry/UDLM-0.1-SCOPE.md`) already
exist in the `use-cases/` corpus under a different handle, and which are genuinely absent. The corpus
is the broader register (149 entries) and **should contain the 21**; when this was written, **none of
the 21 resolved** and all 23 flow citations dangled.

**Why it matters:** every `uc-NN-*.md` flow ends with `UC source: <handle>` — the one pointer that makes
a flow traceable back to its authoritative scenario (success criteria, actors, refusal cases). Without
it an engineer reading a flow has nowhere to go.

**State as of 2026-08-07:** 7 mapped (section A), 14 to author (section B), 0 unresolved. 14 of 44
citations resolve; the rest are declared debt in `tests/uc_traceability_baseline.txt`, which only
shrinks — `tests/check_uc_traceability.py` fails if a fixed pointer re-breaks OR if a resolved one is
left in the baseline.

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
| 09 | `libvirt-vm-provider/dependency-failure-impact` | `intent-fulfillment/operational-dependency-cascade` | **Ruled 2026-08-07.** Two of three criteria covered (unmet dependency named, dependent blocked). The third — blast-radius derivable — is uncovered and tracked below. |
| 17 | `libvirt-vm-provider/provider-registration-capability` | `osac/cloud-provider-registration` | **Ruled 2026-08-07.** The OSAC framing is additive: proving registration + declared capability + advertised capacity for a sovereign cloud proves the generic mechanism. |
| 18 | `cross-domain/provider-portable-rebuild` | `osac/provider-portability-new-cloud` | **Ruled 2026-08-07.** Same — portable intent becoming eligible on another provider, with naturalization at that provider's edge. |

## B — Absent: no corpus entry covers this scenario

Ten from the first pass, plus UC-07, 08, 10, and 16 from the section-C rulings — **fourteen**.

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
| 01 | `libvirt-vm-provider/vm-resource-representation` | `compute/provision-vm-standard` | UC-01 is about the **type**: what `Compute.VM` is made of (spec, lifecycle intent, realized status). The corpus entry is a provisioning scenario that *uses* the type. Check the `scoped-class/` set before authoring. |
| 07 | `dcm-core/udlm-dependency-graph-data-model` | `intent-fulfillment/*` (9 entries) | **Ruled.** That set proves how dependencies *behave*; UC-07 claims what the graph *is* — `edge_type`s as declared data, fault-domain and blast-radius derived from them. |
| 08 | `libvirt-vm-provider/cross-provider-dependency-ordering` | `intent-fulfillment/request-dependency-atomic` | **Ruled.** That entry is atomicity across peer VMs. UC-08 is `depends_on` crossing *provider boundaries*, converging topologically and tearing down in reverse. |
| 10 | `cross-domain/dynamic-rehydration` | 3 domain-specific rehydration entries | **Ruled.** Each proves rehydration in its domain; none asserts UC-10's claim that the plan is *derived from stored intent and the live graph, never replayed*. |
| 16 | `…/policy-override-approval` | `change-control/expedite-break-glass` | **Ruled.** Shares the elevated-approver ceremony but governs *change windows*. UC-16 is policy override — time-scoped, hard policies unoverridable, suppressed events audit-linked. |

## C — Rulings (closed 2026-08-07)

All seven resolved. Three became mappings (folded into section A above); four moved to section B.

| UC | Ruling | Why |
|---|---|---|
| 07 | **Author** | The `intent-fulfillment/` set proves how dependencies *behave*; UC-07 claims what the graph *is* — ordering `edge_type`s as declared data, with fault-domain and blast-radius derived from them. Different assertion, no home record. |
| 08 | **Author** | Decided by evidence, not judgment: `request-dependency-atomic` is ten peer VMs coupled as a unit — atomicity. UC-08 is `depends_on` crossing *provider boundaries*, converging topologically and tearing down in reverse. Different property. |
| 09 | **Map** → `operational-dependency-cascade`, with the blast-radius gap tracked. |
| 10 | **Author** | The three rehydration entries prove it works per domain; UC-10's claim is that the plan is *derived from stored intent and the live graph, never replayed from a recorded sequence*. That is the rehydration tenet, and no record states it. |
| 16 | **Author** | Decided by evidence: `expedite-break-glass` shares the elevated-approver ceremony but governs *change windows*. UC-16 is policy override — time-scoped grants, hard policies unoverridable, suppressed events audit-linked. Same ceremony, different mechanism. |
| 17 | **Map** → `osac/cloud-provider-registration`. |
| 18 | **Map** → `osac/provider-portability-new-cloud`. |

### Open gap from the UC-09 ruling

**Blast-radius derivability has no corpus coverage.** UC-09's third criterion — *impact / blast-radius
of the missing dependency is derivable from the graph* — is in no entry, and `operational-dependency-cascade`
does not carry it. It is the same derived-property claim UC-07 makes, so the two should be settled
together: whichever record asserts that fault-domain and blast-radius are *derived* from the declared
graph (ADR-010) is where this criterion belongs.

---

## Two structural problems the mapping exposes

**Six scope handles are document paths, not use cases.** UC-12, UC-14, UC-15, UC-16, UC-19, and UC-21
are spelled `docs/spec/contracts/…` and `docs/spec/governance/…` in the scope register's handle column.
A document is not a use case; those rows never had a corpus handle to dangle *from*. This is why the
`docs/spec/*` rows cluster in section B — the register recorded where the *requirement* is written, not
what the *scenario* is.

**The `libvirt-vm-provider/*` and `dcm-core/*` namespaces do not exist in the corpus at all.** Five scope
UCs use them. The corpus organizes by domain (`compute/`, `storage/`, `network/`) rather than by
provider, so those five need a namespace decision, not just a rename.

## What remains

**Author 14 corpus entries** (section B). Before writing each, check the near-miss column's entry one
more time — section B's confidence is high for 04/12/20 and for the four section-C rulings, medium for
the rest, since those were assessed against closest candidates rather than all 149 entries.

**Settle blast-radius derivability** (the UC-09 gap above) together with UC-07 — they are the same
derived-property claim.

**Decide two namespace questions** the mapping exposed, both of which affect how the remaining entries
are named:
- The six document-path rows need real use-case handles, since a document is not a scenario.
- `libvirt-vm-provider/*` and `dcm-core/*` do not exist in the corpus, which organizes by domain. Three
  such rows remain unmapped (01, 05, 08).

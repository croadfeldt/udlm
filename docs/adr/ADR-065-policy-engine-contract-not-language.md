# UDLM ADR-065: UDLM specifies the policy-engine **contract**, never the predicate language

**Status:** Proposed (croadfeldt upstream) — **requires engineering ratification**; maintainer decision 2026-08-06
**Date:** 2026-08-06
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)

**Background — read first (the cold reader's on-ramp; skip if you have the context).** Each cited once with what it settles.
- **`policy-contract.md` §7.2a** (built-in vs delegated engine): already states that an external engine "is, in effect, a *Provider of policy decisions*, bound by the contract, not by shared storage." This ADR promotes that from a footnote to the organizing principle and makes the model hold to it.
- **ADR-008** (the the substrate and its control plane boundary): access **determination** is external; UDLM carries the data and the contract, never the decision procedure.
- **The drift ruling** (2026-07): neither UDLM nor the control plane has a built-in action for a drift finding — policies dictate what happens. Same shape: the model carries the facts, the decision lives elsewhere.
- **T9** (core tenet): the substrate never translates into a provider's native spec. A provider's internal implementation is opaque to UDLM; so is an engine's.

---

## Decision

**UDLM specifies what a policy engine *consumes* and what it *returns*. It does not specify how the engine decides.**

Concretely, UDLM owns:

1. **The fact vocabulary** — the governed set of facts an engine may reference (`registry/taxonomies/policy-fact.yaml`, 33 terms under the four §2.1 sources). This is the "reference the correct information" requirement made mechanical.
2. **The evaluation context** — what the control plane sends the engine (§7.1).
3. **The decision and constraint shapes** — what comes back, specified per `policy_type` (validation → `decision`, placement → `constraints`, override → `scope` + `expires_at`), and the re-entrant convergence contract (§7.2).
4. **The audit obligations** on both directions.

The engine owns the predicate language, evaluation strategy, conflict resolution, and convergence mechanics. A policy record carries its rule body in `match.rule` — **opaque to UDLM, which never parses, validates, or interprets it.**

## What was wrong

`policy.schema.json` specified the engine's comparison vocabulary: `match.conditions[].operator` with `eq / ne / in / not_in / exists / not_exists / matches / gt / lt / gte / lte`. That is engine mechanism living in the data model.

Being unenforced is what made it visible. The same vocabulary had forked into **five disagreeing spellings**, none validated by anything:

| Where | Spelling |
|---|---|
| `policy.schema.json` | `eq` `ne` `gte` `lte` `matches` |
| `policy-contract.md` §2.5 | `equals` `not_equals` `minimum` `maximum` `contains` `starts_with` |
| `layering-and-versioning.md` | `and` `contains` `not_contains` |
| `governance-matrix.md` | `includes` `minimum` |
| `operational-models.md` | `equals` `in` |

Two surfaces were outright fictional. `all_of` / `any_of` advertised "nested boolean composition" but `$defs/condition` was flat with `additionalProperties: false` — **it could not nest**, and had zero users. `condition_logic: all|any` appeared in every doc example and **was absent from the schema entirely**.

Nobody noticed because none of it was load-bearing for anything UDLM owns. That is the diagnosis, not an aside: a vocabulary the model does not need is a vocabulary the model cannot keep honest.

## Alternatives considered

**Keep a portable minimum condition form.** Freeze a small engine-neutral `field`/`operator`/`value` shape so a policy record stays readable by a peer, not only its decisions. *Rejected:* it is still engine mechanism in the model, and a frozen-but-present vocabulary invites exactly the drift that produced five spellings. The portability goal is met better by the facts plus the decision shape — a peer can read what a policy binds to and what it produces without being able to evaluate it.

**Adopt CEL for policy predicates.** The industry converged here for admission-time policy (Kubernetes ValidatingAdmissionPolicy, Istio, Envoy RBAC, GCP IAM Conditions), with a formal spec, guaranteed termination, and cost bounds — genuinely attractive for tenant-authored predicates at a commit barrier. *Rejected:* UDLM does not pick a policy language. Choosing CEL would move computation into policy text and out of governed data, which cuts against the model's own stance — a comparison the model performs (`quota.exceeded`, `graph.has_cycle`) is a fact an auditor can read and verify; a comparison left to policy text is one they must re-derive. The control plane will likely adopt OPA/Rego, and that is an implementation choice, which is the point.

**Add RE2 regex to URF so policies could target precisely.** The motivating case was precise policy targeting — glob over-matches (`worker*` catches `worker3` as well as `worker03`), and on an exemption policy over-matching is fail-open. *Rejected:* the case moved to the engine, and Rego has `regex.match()`. URF retains data selection over *declared* fields, where glob plus `=in=` suffices and precision belongs to the field rather than to parsing an advisory handle (identifier-scheme §9 — handles are advisory). Declining it also avoids declaring a regex dialect, percent-encoding URL-illegal metacharacters, a ReDoS surface in criterion evaluation, and opaque-literal identity. The refusal is enforced as URF-008.

**Keep RSQL as the policy predicate language** (the original PR 5 plan: convert `match.conditions` to URF). *Rejected:* RSQL is strong for filtering and weak for policy — no functions, no collection quantifiers, no field-to-field comparison. It silently accepts `quota.used=gt=quota.limit` and compares against the literal string `"quota.limit"`. Unifying on it would have made the model *specify* a predicate language, which is the thing this ADR says it must not do.

## Consequences

**A policy record stays a complete governed artifact.** Identity, lifecycle, provenance, and audit (§6) all still apply; only the comparison moved. A peer that does not run this engine reads the record's facts, decision shape, and audit obligations, and refuses to evaluate rather than guessing — `match.rule.engine` names the dialect so that refusal is informed — as a **canonical term** in the `policy-engine` taxonomy, not a free string, since a refuse-or-evaluate decision cannot rest on one (`rego`/`Rego`/`opa` would be three answers to one question). Governing the name is not picking the engine: the vocabulary is open, and a new engine enters by the curation ladder (ADR-039) rather than by a spec change. `builtin` names the evaluating implementation's own engine — not portable, and knowably so. The rule BODY is optional by contract: under §7.2a's delegated mode the implementation never stores the external engine's policies, so a record may declare its facts and carry no body — but it still names the engine, because the peer's decision depends on the dialect and not on whether the body travels.

**Policies become analyzable without being evaluated.** Declaring facts gives impact analysis a real edge: when a fact changes shape, the policies that read it are known. That was not possible when the dependency was buried inside a predicate.

**Two enforcement gates, both negative-probed:**
- `tests/check_policy_facts.py` — PFACT-001/002: every referenced fact resolves; every term has a source subtree.
- `tests/check_policy_boundary.py` — PBND-001/002/003: no predicate-operator vocabulary, no boolean composition, and a policy's match declares facts. It matches on operator *values* rather than key names, because the key is the easy thing to rename and the vocabulary is the actual smell.

**Governance-matrix §2.6 stays.** Its four-axis block (subject / data / target / context) names **axes, not operators** — which dimensions a boundary decision is made over. That is governance structure (ADR-008) and therefore UDLM's. Its `ALLOW_WITH_CONDITIONS` obligations are re-expressed as declarative requirements rather than comparisons.

**Out of scope, tracked separately.** A layer's `activation_condition` and a conditional dependency's `condition` carry predicates too, evaluated by the control plane's *assembly* engine rather than a policy engine. Same boundary question, separate ruling — neither is schema-backed today (the only schema mention is the exclusion-reason enum value `activation_condition_false`), so nothing is load-bearing while it waits.

## What this does NOT change

UDLM still specifies **what a policy produces**. The decision and constraint shapes are the contract's other half and are unaffected — removing the predicate language does not weaken what a policy is obliged to return, nor the audit trail it must leave.

# Authoring a policy

**What this is.** The procedure for adding a Policy — a validation rule, a placement constraint, an
override, a change-control schedule — to the UDLM registry so DCM's Policy Engine can evaluate it and CI
will accept it. A Policy is **data**: UDLM carries the record, DCM decides. Follow the five steps and the
gates pass; skip one and a gate names it.

> **Read once first:** [`../../CONTRIBUTING.md`](../../CONTRIBUTING.md) (the DOC-001 writing standard and the
> subject-scoped-PR rule) and [`README.md`](README.md) (the universal contract every artifact meets).

## 1. When to use — and when not

Author a Policy when you are encoding a **decision the estate makes at request or lifecycle time** —
allow/deny, permit/block, a field mutation, a placement constraint, a recovery action, an override of a soft
rule. The schema's `policy_type` enum is the menu: `validation`, `transformation`, `gating`, `recovery`,
`orchestration_flow`, `governance_matrix_rule`, `placement`, `lifecycle`, `itsm_action`, `override`.

**When *not* to:**

- You are describing *what a thing is*, not *what to decide about it* — that is a **layer** (data
  contribution, [`reference-data.md`](reference-data.md)) or a **resource type**, not a Policy. Layers carry
  the *what*; Policies decide the *how* (`layer.schema.json` description).
- You want a new *kind* of temporal rule (a maintenance window, a freeze, an expedite). Do **not** mint a new
  `policy_type`. **ADR-053 — change-control is a `schedule` clause family on the existing policy object, not a
  new policy_type; a schedule clause governs *when*, never *whether*.** You add a `schedule` clause to a
  `gating`/`orchestration_flow` policy; the evidence gate stays a separate `gating` clause the schedule can
  never reference away. (The `schedule` block is ratified vocabulary; its JSON-Schema shape lands in the
  implementing PR ADR-053 §"What this does not decide" names — until then, model the timing decision as the
  Validation Policy it sits on and cite ADR-053.)
- Before coining any new match source or output field, show no existing one composes to cover it (review
  sweep tenet **T7** — reduce to existing).

## 2. The steps, in order

1. **Write the record** at `registry/instances/<your-policy>.yaml` (or a provider/profile record if it ships
   with one). Set the required fields (`policy.schema.json` `required`): `record_type: policy`, a fresh v4
   `uuid`, `conforms_to: udlm/0.1`, `name`, `version` (semver), `tenant_uuid` (the platform tenant for a
   system-domain policy), `policy_type`, `match`, `output`.
2. **Write `match`** — the conditions that make the policy fire (`match.conditions`, or nested
   `match.all_of`/`any_of`). Each condition is `{field, operator, value}`. `field` is a request/entity
   dot-path or a known source — `data_classification`, `sovereignty_zone`, `tenant_uuid`, `resource_type`,
   the `graph.*` cycle/blast-radius diagnostics, `quota.*`, `reserved.*` during reconciliation (see the
   `match.conditions.field` description for the full source list).
3. **Write `output`** — what the policy produces when it fires. The inner shape is **conditional on
   `policy_type`** (the schema's `allOf`): a `validation` output requires `decision` ∈
   allow/deny/pass/fail; `gating` requires `decision` ∈ permit/block/dual_approval; `placement` requires
   `constraints`; `transformation` requires `mutations`; `override` requires `scope` **and** `expires_at`.
4. **Set precedence and enforcement.** `domain` sets precedence scope (`resource_type` override wins over
   `tenant` wins over profile default); `enforcement` is `hard` (blocking) or `soft` (advisory).
   `lifecycle_scope.operations` names which operations it evaluates on — compliance-class validation and
   `governance_matrix_rule` must include `all`.
5. **If the policy states a normative rule, give it a rule-ID.** A normative policy rule carries a registered
   `PREFIX-NNN` (e.g. `POL-003`) — **ADR-028: one prefix = one rule family = one home file; the prefix is
   registered in `registry/rule-id-registry.yaml` before use, and a rule is *defined* in exactly one home.**
   Register the prefix first; an unregistered one fails CI.

### The two special cases the schema pins hardest

- **Override** (`policy_type: override`). `output.target_policy_uuid` names the **soft** policy it suppresses
  — **hard-enforcement policies are unoverridable (POL-003)**. `output.scope` is the narrowed match scope,
  **never global** (§18.1). `output.expires_at` is **mandatory** — overrides are time-bounded (POL-009).
- **Placement** (`policy_type: placement`, DCM ADR-019). `output.constraints` carries the spread/affinity/
  jurisdiction requirements; the provider's `topology_capability` (see [`provider-api.md`](provider-api.md))
  is what a constraint is matched against.

## 3. Completeness checklist — and the gate that enforces each

| Ships with the policy | Why | Gate |
|---|---|---|
| Validates against `policy.schema.json` (required fields; type-correct `output` for its `policy_type`) | Valid by construction | `registry/tools/validate.py` |
| Fresh `uuid`; a change to a published policy bumps `version` (never edits in place) | Identity is honest (ADR-051) | `registry/tools/validate.py`, `tests/check_identity_integrity.py` |
| Every normative rule-ID uses a registered, single-home prefix | One definition per rule (ADR-028) | `tests/check_single_source.py` |
| No retired vocabulary in the prose (use the current term — e.g. "Validation Policy") | Terminology discipline (TERM-001) | `tests/check_terminology.py` |

## 4. A worked pointer

Copy [`../../registry/instances/example-policy.yaml`](../../registry/instances/example-policy.yaml) — a
`validation`/`compliance` policy: it denies any request whose `data_classification` is `eu_personal` unless
its `sovereignty_zone` is EU, with `enforcement: hard`, `lifecycle_scope.operations: [all]`, and an
`output: {decision: deny, reason: …}`. It shows the match→output shape, the compliance-basis citation, and
the review-deadline field in one small record.

For an **override**, the shape is: `policy_type: override`, `output: {target_policy_uuid: <soft policy>,
scope: <narrowed match>, expires_at: <RFC 3339 Z>}`. For a **change-control schedule**, cite ADR-053 and the
change-control flow [`../flows/change-control-adoption.md`](../flows/change-control-adoption.md) — the
schedule clauses attach to a Validation Policy, they are not a policy of their own.

## 5. Run the gates

From the repo root:

```console
$ python registry/tools/validate.py
...
ALL VALID — 0 invalid

$ python tests/check_single_source.py
rule-id single-source: 46 registered prefix(es); 400 rule IDs across the normative surface; 0 collide (0 baselined); 2 sanctioned co-home(s), 0 spread-debt entr(y/ies).
OK — every rule-ID prefix is registered; every ID has a single definition.

$ python tests/check_terminology.py
550 files scanned, 0 terminology violation(s)
```

Each exits `0`. `validate.py` prints an advisory change-impact section before the verdict — that is not a
failure; the line that gates you is `ALL VALID — 0 invalid`. A non-zero exit names the record and the field.

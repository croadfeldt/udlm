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
rule. The schema's `policy_type` enum is the menu: `validation`, `transformation`, `recovery`,
`orchestration_flow`, `governance_matrix_rule`, `placement`, `lifecycle`, `itsm_action`, `override`.

**When *not* to:**

- You are describing *what a thing is*, not *what to decide about it* — that is a **layer** (data
  contribution, [`reference-data.md`](reference-data.md)) or a **resource type**, not a Policy. Layers carry
  the *what*; Policies decide the *how* (`layer.schema.json` description).
- You want a new *kind* of temporal rule (a maintenance window, a freeze, an expedite). Do **not** mint a new
  `policy_type`. **ADR-053 — change-control is a `schedule` clause family on the existing policy object, not a
  new policy_type; a schedule clause governs *when*, never *whether*.** You add a `schedule` clause to
  the policy that governs the change; the evidence gate stays a separate `match` rule the schedule can
  never reference away. `schedule` is a property of `policy.schema.json`: an array of clauses, each with
  a `kind` of `window`, `freeze`, `expedite` or `precondition`.
- Before coining any new match source or output field, show no existing one composes to cover it (review
  sweep tenet **T7** — reduce to existing).

## 2. The steps, in order

1. **Write the record** at `registry/examples/<your-policy>.yaml` (or a provider/profile record if it ships
   with one). Set the required fields (`policy.schema.json` `required`): `record_type: policy`, a fresh v4
   `uuid`, `conforms_to: udlm/0.1`, `name`, `version` (semver), `tenant_uuid` (the platform tenant for a
   system-domain policy), `policy_type`, `match`, `output`.
2. **Write `match`** — what the policy binds to. `match.facts` lists the facts the policy reads, each a
   term in the policy-fact taxonomy (`registry/taxonomies/policy-fact.yaml`): `data_classification`,
   `sovereignty_zone`, `tenant_uuid`, `resource_type`, the `graph.*` cycle and blast-radius diagnostics,
   `quota.*`, or `reserved.*` during reconciliation. `match.rule` carries the engine-native rule body
   (`engine` plus the body), which UDLM never parses. Declaring a fact says the policy reads it, not what
   it concludes; `tests/check_policy_facts.py` (PFACT-001) refuses a fact the taxonomy does not carry.
3. **Write `output`** — what the policy produces when it fires. The inner shape is **conditional on
   `policy_type`** (the schema's `allOf`): a `validation` or `governance_matrix_rule` output requires
   `decision` (`allow`/`deny`/`pass`/`fail` for validation); `recovery` requires `action`;
   `orchestration_flow` requires `ordered`; `placement` requires `constraints`; `transformation` requires
   `mutations`; `override` requires `scope` **and** `expires_at`.
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

Copy [`../../registry/examples/example-policy.yaml`](../../registry/examples/example-policy.yaml) — a
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
rule-id single-source: 54 registered prefix(es); 507 rule IDs across the normative surface; 0 collide (0 baselined); 2 sanctioned co-home(s), 0 spread-debt entr(y/ies).
vocabulary single-source: 97 closed list(s) >= 4 members across the authored registry; 1 declared in more than one file (0 baselined).
OK — every rule-ID prefix is registered; every ID has a single definition.

$ python tests/check_terminology.py
841 files scanned, 0 terminology violation(s)
```

Each exits `0`. `validate.py` prints an advisory change-impact section before the verdict — that is not a
failure; the line that gates you is `ALL VALID — 0 invalid`. A non-zero exit names the record and the field.

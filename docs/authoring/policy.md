# Authoring a policy

**What this is.** The procedure for adding a Policy — a validation rule, a placement constraint, an
override — and the Policy Configuration that gives it one deployment's values, so DCM's Policy Engine can
evaluate it and CI will accept it. Both are **data**: UDLM carries the records, DCM decides. Follow the
steps and the gates pass; skip one and a gate names it.

> **Read once first:** [`../../CONTRIBUTING.md`](../../CONTRIBUTING.md) (the DOC-001 writing standard and the
> subject-scoped-PR rule) and [`README.md`](README.md) (the universal contract every artifact meets).

## 1. Two records, and which one you are writing

A **policy** holds logic: the facts it reads, the rule, the parameters it accepts and what it produces. A
**policy configuration** holds the values one deployment gives that logic: the parameter values, the tenant,
the scope, the enforcement level, the schedule. **POL-011 — a policy holds logic and no deployment's values;
a policy with no active configuration decides nothing** (policy-contract §9).

Ask of each field: would a second deployment keep it unchanged? If yes, it is the policy's. If no, it is
the configuration's.

- A new rule needs both records.
- The same rule with other values, another tenant or another strictness needs only a new configuration.
- A change to the rule is a new version of the policy; each configuration moves to it by moving its pin.

Author a policy when you are encoding a **decision the estate makes at request or lifecycle time** —
allow/deny, permit/block, a field mutation, a placement constraint, a recovery action, an override of a soft
rule. The schema's `policy_type` enum is the menu: `validation`, `transformation`, `recovery`,
`orchestration_flow`, `governance_matrix_rule`, `placement`, `lifecycle`, `itsm_action`, `override`.

**When *not* to:**

- You are describing *what a thing is*, not *what to decide about it* — that is a **layer** (data
  contribution, [`reference-data.md`](reference-data.md)) or a **resource type**, not a Policy. Layers carry
  the *what*; Policies decide the *how* (`layer.schema.json` description).
- You want a new *kind* of temporal rule (a maintenance window, a freeze, an expedite). Do **not** mint a new
  `policy_type`. **ADR-053 — change-control is a `schedule` clause family, not a new policy_type; a schedule
  clause governs *when*, never *whether*.** The clauses are a deployment's values, so you add them to the
  **configuration** of the policy that governs the change. The evidence check stays the policy's `match`
  rule, on a different record, where no clause can reference it away. `schedule` is a property of
  `policy-configuration.schema.json`: an array of clauses, each with a `kind` of `window`, `freeze`,
  `expedite` or `precondition`.
- Before coining any new match source or output field, show no existing one composes to cover it (review
  sweep tenet **T7** — reduce to existing).

## 2. The policy, in order

1. **Write the record** at `registry/examples/<your-policy>.yaml` (or a provider record if it ships with
   one). Set the required fields (`policy.schema.json` `required`): `record_type: policy`, a fresh v4 `uuid`,
   `conforms_to: udlm/0.1`, `name`, `version` (semver), `policy_type`, `match`, `output`. It carries no
   `tenant_uuid`, `domain` or `enforcement`: the schema refuses them here.
2. **Write `match`** — what the policy binds to. `match.facts` lists the facts the policy reads, each a
   term in the policy-fact taxonomy (`registry/taxonomies/policy-fact.yaml`): `data_classification`,
   `sovereignty_zone`, `tenant_uuid`, `resource_type`, the `graph.*` cycle and blast-radius diagnostics,
   `quota.*`, or `reserved.*` during reconciliation. `match.rule` carries the engine-native rule body
   (`engine` plus the body), which UDLM never parses. Declaring a fact says the policy reads it, not what
   it concludes; `tests/check_policy_facts.py` (PFACT-001) refuses a fact the taxonomy does not carry.
3. **Declare the parameters** in `parameter_schema`, if the rule needs a value a deployment chooses: an
   allowed-zone list, a threshold, which of two readings applies. It is a JSON Schema for the
   configuration's `parameters` object. Leave it out when the rule needs none. A literal in the rule body
   that a second deployment would change is a parameter you have not declared yet.
4. **Write `output`** — what the policy produces when it fires. The inner shape is **conditional on
   `policy_type`** (the schema's `allOf`): a `validation` or `governance_matrix_rule` output requires
   `decision` (`allow`/`deny`/`pass`/`fail` for validation); `recovery` requires `action`;
   `orchestration_flow` requires `ordered`; `placement` requires `constraints`; `transformation` requires
   `mutations`; `override` requires `scope` **and** `expires_at`.
5. **If the policy states a normative rule, give it a rule-ID.** A normative policy rule carries a registered
   `PREFIX-NNN` (e.g. `POL-003`) — **ADR-028: one prefix = one rule family = one home file; the prefix is
   registered in `registry/rule-id-registry.yaml` before use, and a rule is *defined* in exactly one home.**
   Register the prefix first; an unregistered one fails CI.

## 3. The configuration, in order

1. **Write the record** at `registry/examples/<your-configuration>.yaml`. Required
   (`policy-configuration.schema.json`): `record_type: policy_configuration`, a fresh v4 `uuid`,
   `conforms_to`, `name`, `version`, `tenant_uuid` (the platform tenant for a system-domain configuration)
   and `configures`.
2. **Pin the policy** in `configures`: the policy's handle or `uuid/<v4>`, then `@` and its version
   (`data-residency-gate@3.0.0`). **POL-012 — a configuration configures exactly one policy, pinned; a new
   version of the policy reaches a deployment only when the configuration moves the pin.** The schema
   refuses a reference with no pin.
3. **Give the parameters** the policy declares, in `parameters`. **POL-013 — the parameters satisfy the
   policy's `parameter_schema`, and none is supplied that it does not declare.** A misspelled name fails the
   gate instead of being carried and never read.
4. **Set precedence, scope and enforcement.** `domain` sets precedence scope (`resource_type` wins over
   `tenant`, policy-contract §4); `enforcement` is `hard` or `soft`; `lifecycle_scope.operations` names
   which operations it evaluates on — a configuration of a compliance-class validation policy or a
   `governance_matrix_rule` must include `all`.
5. **To try it first, set `status: {state: proposed}`.** The policy runs on real traffic with these values
   and its output is logged, never applied (POL-004). A policy that is itself `proposed` is provisional
   logic: every configuration of it stays `proposed` until the policy is `active` (POL-015).
6. **A profile turns it on.** A profile's `contains[]` entry names the configuration and says `required`,
   `advisory` or `off`. **POL-014 — a profile holds no values for a policy configuration**; the entry
   carries no `settings`.

### The two special cases the schema pins hardest

- **Override** (`policy_type: override`). `output.target_configuration_uuid` names the **soft** configuration
  it suppresses — **a hard configuration is unoverridable (POL-003)**. `output.scope` is the narrowed match
  scope, **never global** (§18.1). `output.expires_at` is **mandatory** — overrides are time-bounded (POL-009).
- **Placement** (`policy_type: placement`, DCM ADR-019). `output.constraints` carries the spread/affinity/
  jurisdiction requirements; the provider's `topology_capability` (see [`provider-api.md`](provider-api.md))
  is what a constraint is matched against.

## 4. Completeness checklist — and the gate that enforces each

| Ships with the policy | Why | Gate |
|---|---|---|
| Each record validates against its schema (required fields; type-correct `output` for the `policy_type`; no deployment value on the policy) | Valid by construction | `registry/tools/validate.py` |
| The configuration pins one policy that exists at that version, and its parameters satisfy the policy's `parameter_schema` | A configuration that points at nothing, or misspells a parameter, decides nothing and says so nowhere | `tests/check_policy_configurations.py` |
| Fresh `uuid`; a change to a published record bumps `version` (never edits in place) | Identity is honest (ADR-051) | `registry/tools/validate.py`, `tests/check_identity_integrity.py` |
| Every normative rule-ID uses a registered, single-home prefix | One definition per rule (ADR-028) | `tests/check_single_source.py` |
| No retired vocabulary in the prose (use the current term — e.g. "Validation Policy") | Terminology discipline (TERM-001) | `tests/check_terminology.py` |

### A worked pointer

Copy [`../../registry/examples/example-policy.yaml`](../../registry/examples/example-policy.yaml) and
[`../../registry/examples/example-policy-configuration.yaml`](../../registry/examples/example-policy-configuration.yaml).
The policy is a `validation`/`compliance` rule: it denies a request whose `data_classification` is one the
deployment restricts unless its `sovereignty_zone` is one the deployment allows, and it declares those two
lists as parameters. The configuration pins it, supplies `eu_personal` and three EU zones, and sets
`enforcement: hard`, `lifecycle_scope.operations: [all]`, the compliance-basis citation and the review
deadline.
[`example-policy-configuration-residency-trial.yaml`](../../registry/examples/example-policy-configuration-residency-trial.yaml)
gives the same policy other values, in shadow mode.

For an **override**, the shape is: `policy_type: override`, `output: {target_configuration_uuid: <soft
configuration>, scope: <narrowed match>, expires_at: <RFC 3339 Z>}`. For a **change-control schedule**, cite
ADR-053 and the change-control flow
[`../flows/change-control-adoption.md`](../flows/change-control-adoption.md) — the schedule clauses attach to
the configuration of a Validation Policy, they are not a policy of their own
([`example-policy-configuration-change-window.yaml`](../../registry/examples/example-policy-configuration-change-window.yaml)).

## 5. Run the gates

From the repo root:

```console
$ python registry/tools/validate.py
...
ALL VALID — 0 invalid

$ python tests/check_policy_configurations.py
policy-configurations: 6 configuration(s) over 5 policy record(s); 1 profile(s) read
OK — every configuration pins one policy and satisfies its parameters; no profile entry holds a policy's values

$ python tests/check_single_source.py
rule-id single-source: 54 registered prefix(es); 507 rule IDs across the normative surface; 0 collide (0 baselined); 2 sanctioned co-home(s), 0 spread-debt entr(y/ies).
vocabulary single-source: 97 closed list(s) >= 4 members across the authored registry; 1 declared in more than one file (0 baselined).
OK — every rule-ID prefix is registered; every ID has a single definition.

$ python tests/check_terminology.py
841 files scanned, 0 terminology violation(s)
```

Each exits `0`. `validate.py` prints an advisory change-impact section before the verdict — that is not a
failure; the line that gates you is `ALL VALID — 0 invalid`. A non-zero exit names the record and the field.

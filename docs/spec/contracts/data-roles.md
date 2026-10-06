# UDLM — Data Roles (PROPOSED)

**Related:** [Provider Contract](provider-contract.md) | [Policy Contract](policy-contract.md) | [Governance Matrix](../governance/governance-matrix.md) | [Four States](../foundations/four-states.md)

> **This document maps to: DATA + POLICY + PROVIDER.** It defines the role vocabulary ONCE; records
> reference roles by their short token. It is the single definition; usage is terse.

---

## 1. Two orthogonal axes

Every datum in UDLM sits on two independent classification axes:

| Axis | Question | Governs |
|------|----------|---------|
| **`data_classification`** (existing) | *Who may see it?* (public → classified) | trust boundaries / redaction |
| **`data_role`** (this doc) | *What is it for?* | **dispatch** — what crosses to a provider |

They compose: sensitivity says *whether* a datum may cross a boundary; role says *whether the provider needs it at all*.

## 2. The role vocabulary (defined once)

| `data_role` | Meaning | Crosses to provider? |
|-------------|---------|----------------------|
| **`execution`** | The provider needs it to realize the resource — **the dispatch contract** (domain field values + execution-control data: placement result, credential ref, idempotency key) | **Yes — default** |
| **`assembly`** | Control-plane assembly record: unapplied contributions, excluded layers (the "road not taken") | No (opt-in) |
| **`governance`** | Governance/policy decision metadata | No (opt-in) |
| **`audit`** | Audit-only annotations | No (opt-in) |
| **`cost`** | Cost/metering attribution ([ADR-COST-002](../../../docs/adr/ADR-COST-002-cost-metering-linkage-hooks.md)) | No (opt-in) |

The enum is extensible. It is defined once, in `registry/common-elements.schema.json` (`data_role`). No role is dispatched by default (DSP-001): a role is what policy reads when it decides what crosses.

## 3. The dispatch rule — zero trust

A provider gets nothing by default. Data crosses for two reasons only: the provider needs it to build the order, or a policy granted it. Both are declared, and both are recorded.

| ID | Rule |
|---|---|
| `DSP-001` | **Deny by default.** The payload to a provider starts empty. Nothing crosses because of where it sits on the record, what role it has, or what the provider wants. Control-plane data (`assembly`, `policies`, `provenance`, `metadata`, `dispatch`, `integrity`, `audit`, and any element declared non-execution) never crosses. |
| `DSP-002` | **The bound class defines required.** The elements of the class the provider binds are the order. They are admitted. A class element with a non-execution `role`, a record's `roles` override, and a provider's `accepts_roles` each remove elements. None can add. |
| `DSP-003` | **Beyond required, only by policy.** A provider may declare data it needs beyond its class (`requests_data`, PRV-013). The control plane assumes nothing. Policy grants, narrows or refuses each need, and may strip any admitted element. Whether a policy's author may grant is authorization (`governance/accreditation-and-authorization-matrix.md`), not dispatch. |
| `DSP-004` | **The receipt.** The requested record's `dispatch` block lists the provider, every path that crossed, each grant with its policy, and each strip with its policy. What a provider saw is readable from the record alone. Gate: `tests/check_dispatch_slice.py`. A request refused before a provider was selected still carries the receipt: `provider` is the placement authority and `admitted` is empty. Nothing crossed, and the record says so; every requested record has a receipt, without exception. |

The realized record gets no control-plane data either: the provider reports `fields` and `outputs`, nothing more. `native_passthrough` (DATA-001) crosses as an element of the Provider Class under DSP-002, never as a side channel.

## 4. Usage — field- and section-level, succinct

A class declares an element's role once (`role` on the element). A record may narrow further with a `roles` map keyed by dot-path. Absent means `execution`: required by the bound class, admitted under DSP-002. List only the exceptions.

```yaml
states:
  requested:
    fields: { cpu: {…}, memory: {…} }          # role: execution (default) → dispatched
    roles:
      cost_attribution: cost                     # field-level override
      diagnostics: assembly                       # section-level (prefix) override
    assembly:                                     # the non-dispatched section (role: assembly)
      unapplied:
        - { field: memory, source: {kind: layer, id: <uuid>}, attempted_value: "32GB",
            disposition: overridden, reason: "tenant cap layer set 16GB", at: "2026-07-07T…Z" }
      excluded_layers:
        - { layer_uuid: <uuid>, reason: activation_condition_false }
```

**Cascade / precedence:** field-level path **>** section-level prefix **>** record default (`execution`). One rule.

## 5. Providers declare, policy decides

A provider's registration says what roles it will accept (`accepts_roles`) and what data it needs beyond its class (`requests_data`). Both are asks. The first only narrows. The second is answered per need by policy (DSP-003). An undeclared need is not considered.

## 6. Policy validates and controls — reuse the Governance Matrix

Role-based dispatch is **not new policy machinery** — the Governance Matrix already fires on every `the control plane → Provider` interaction (policy-contract §857) with `ALLOW / DENY / STRIP_FIELD / REDACT / AUDIT_ONLY`. `data_role` is now a **match source** (parallel to `data_classification`).

- **Default rule:** `STRIP_FIELD` every non-`execution` role at the control plane→Provider boundary.
- **Delivered set** = `accepts_roles` ∩ Governance-Matrix-permitted. Sovereignty/profile can strip a role the provider requested; it can never widen beyond `accepts_roles`.
- **Profile-graded:** `fsi`/`sovereign` strip hard and `AUDIT_ONLY` any widening; `standard` may permit trusted internal providers.

## 7. Data · Policy · Provider

- **Data:** `data_role` is a classification on data (field/section), twin of `data_classification`. `execution` = the dispatch contract; the rest is control-plane.
- **Policy:** which roles reach which provider is Governance-Matrix policy (`data_role` match source); the default strips non-execution.
- **Provider:** declares `accepts_roles` (what it wants) and may tag returned data by role. Never receives more than it opted into and policy permits.

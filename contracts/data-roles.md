# UDLM — Data Roles (PROPOSED)

**Document Status:** 🟡 PROPOSED — see [ADR-PROV-001](../registry/instances/adr-provider-dispatch-role.json)
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
| **`cost`** | Cost/metering attribution ([ADR-COST-002](../registry/instances/adr-cost-metering-linkage.json)) | No (opt-in) |

The enum is extensible (`x-extensible-enum`). **`execution` is the only role dispatched by default.**

## 3. The dispatch rule

> **The provider dispatch payload = the `role: execution` slice of the Requested snapshot** (`states.requested`), and nothing else, unless a provider opts in AND policy permits.

- Non-execution roles (`assembly`, …) are **control-plane only**: they MUST NOT be naturalized into the dispatch payload and MUST NOT be copied into `states.realized`.
- This is the mirror of `native_passthrough` (DATA-001), which is *sanctioned* to cross; role fences everything non-execution.

## 4. Usage — field- and section-level, succinct

Roles are declared with a `roles` map on the snapshot, keyed by dot-path. **Default is `execution`; you list only the non-execution exceptions** — so the common case costs nothing.

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

## 5. Providers opt in — `accepts_roles`

A provider declares `accepts_roles` at registration (provider-contract §2), default `[execution]`. It may request more (e.g. `[execution, assembly]`). Providers may also **tag data they return** (naturalization) by role — a returned datum tagged `assembly` is context, not authoritative realized state.

## 6. Policy validates and controls — reuse the Governance Matrix

Role-based dispatch is **not new policy machinery** — the Governance Matrix already fires on every `DCM → Provider` interaction (policy-contract §857) with `ALLOW / DENY / STRIP_FIELD / REDACT / AUDIT_ONLY`. `data_role` is now a **match source** (parallel to `data_classification`).

- **Default rule:** `STRIP_FIELD` every non-`execution` role at the DCM→Provider boundary.
- **Delivered set** = `accepts_roles` ∩ Governance-Matrix-permitted. Sovereignty/profile can strip a role the provider requested; it can never widen beyond `accepts_roles`.
- **Profile-graded:** `fsi`/`sovereign` strip hard and `AUDIT_ONLY` any widening; `standard` may permit trusted internal providers.

## 7. Data · Policy · Provider

- **Data:** `data_role` is a classification on data (field/section), twin of `data_classification`. `execution` = the dispatch contract; the rest is control-plane.
- **Policy:** which roles reach which provider is Governance-Matrix policy (`data_role` match source); the default strips non-execution.
- **Provider:** declares `accepts_roles` (what it wants) and may tag returned data by role. Never receives more than it opted into and policy permits.

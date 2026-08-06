# Authoring a provider / API

**What this is.** The procedure for declaring a **provider** — a backend that naturalizes portable UDLM
intent into some native form (a KubeVirt VM, a ZFS dataset, a cost feed). You author a *capability
declaration*: which external standards the provider speaks and which versioned, accreditable capabilities it
offers. UDLM carries the declaration as data; DCM matches, negotiates, and drives implementation.

> **Read once first:** [`../../CONTRIBUTING.md`](../../CONTRIBUTING.md) and [`README.md`](README.md) (the
> universal contract).

## 1. When to use — and when not

Author a provider declaration when a **mature tool already owns a mechanism** and you are wrapping it so the
estate can drive it through portable intent. That is the whole design stance: **DCM ADR-023 — a provider
wraps a mature tool at the naturalization boundary; the control plane owns cross-tool intent and the estate
graph, the provider owns the native translation (tenet T8, adopt tools by reference — don't reimplement the
mechanism).** Everything past that boundary (how the provider talks to its tool) is the provider's business
and never enters the portable model.

**When *not* to:**

- You are inventing a portable resource shape — that is a **resource type**, not a provider. A provider
  *realizes* types; it does not define them.
- You want to translate a native value back into intent. Don't — the chosen native class is a **realized
  fact**, recorded as an output, never written into portable intent (ADR-036; see
  [`reference-data.md`](reference-data.md)).
- You are governing *who may invoke* a provider function — that is the RBAC record, not the capability
  declaration. Both live here (§2), but they are different files with different schemas.

## 2. The steps, in order

### A. The capability declaration — `provider-adopted-standards.schema.json`

1. **Write the record** at `docs/spec/contracts/provider-contract.md` §2 (the registration payload — standing provider artifacts retired 2026-08-04; capabilities are the Provider Classes a provider supports or injects at DCM registration) (e.g. `service/` or `information/`). Set
   the required top level (`provider-adopted-standards.schema.json` `required`): `provider` and
   `adopted_standard_support`.
2. **`provider`** — `name`, a v4 `uuid`, and `version`. **The `uuid` is frozen at registration and never
   rotates on edit (ADR-051): it is the `subject_uuid` every accreditation binds to; a moved anchor orphans
   every attestation.** `version` is the declared surface's semver — surface changes bump it under the publish
   law; changes *past* the naturalization boundary are free. Set `kind`: `service`, `information`, or
   `composite`.
3. **`adopted_standard_support[]`** — one entry per external standard, each `{standard, supports, direction}`
   (e.g. `{standard: KubeVirt, supports: ">=1.0", direction: consume}`). `supports` is a pin/wildcard/range;
   range *resolution* is DCM policy, not the schema. **Every `standard` token must already be registered —
   ADOPT-001: every provider standard token resolves to a `Covers:` entry in
   [`../../registry/standards-adoption-register.md`](../../registry/standards-adoption-register.md); an
   unregistered standard is a hard failure because the adoption decision (what/why/license) was never
   recorded.** Register the standard first if it is new.
4. **`capabilities[]`** — the declared, versioned, accreditable units. Each capability is
   `{capability_uuid, version, categories[]}` (+ optional `name`, `covers_types`). The `capability_uuid` is
   **also a frozen accreditation anchor**; `version` bumps on any change to its attested surface and expires
   the grain-3 accreditation until re-attested. Each `category` in `categories[]` is a `(verb × domain)`
   scope (e.g. `realize_resources/Compute`) carrying its own `topology_capability`, `mobility`,
   `operational_capability`, and `sovereignty`. Per-category blocks override `provider_defaults`
   (finest-granularity-wins).

### B. Accreditation — attesting the declaration is trusted

A declared `sovereignty` or `conformance_claim` is a **claim**, not trust. Trust is a separate immutable
record: **ADR-051 — an accreditation binds `subject_uuid` + `capability_uuid` and records the exact
`attested_digests` it reviewed (the in-toto shape, exact-by-default); a version bump changes the digest and
expires the attestation.** Author it against `registry/accreditation.schema.json` when a provider capability
needs a sovereignty/framework attestation to be selectable under a strict profile.

### C. The RBAC record (optional) — `function-capability-matrix.schema.json`

To govern *who may perform which DCM/provider functions*, author a `role_capability` (binds an access-role to
its `permitted_functions`, default-deny) or a `role_assignment` (binds an actor/access-group to a role) — one
of the two `oneOf` shapes in `function-capability-matrix.schema.json`. This is DCM RBAC projected as data
onto the one Governance Matrix; it is distinct from the capability *declaration* in A.

## 3. Completeness checklist — and the gate that enforces each

| Ships with the provider | Why | Gate |
|---|---|---|
| Validates against `provider-adopted-standards.schema.json` | Valid by construction | DCM admission at registration |
| Every `adopted_standard_support[].standard` token resolves in the adoption register | ADOPT-001 — the adoption decision is recorded | DCM admission at registration |
| `provider.uuid` + every `capability_uuid` are canonical v4 and **unique across registered providers** | They are accreditation anchors; a shared anchor lets one attestation cover two subjects | DCM admission at registration |
| Every `supports` range parses (pin / wildcard / comparator) | DCM can resolve it | DCM admission at registration |
| No standard adopted only in prose without a register row | Completeness (report-only review aid) | `tests/check_standards_registered.py` |

## 4. A worked pointer

Copy [`../../contracts/provider-contract.md §2 examples`](../spec/contracts/provider-contract.md)
— a `service` provider that consumes Redfish/KubeVirt/Kubernetes and declares three capabilities (VM,
Container, Cluster lifecycle), each spanning several `(verb × domain)` categories with per-category
`topology_capability`, `operational_capability`, and (on the container capability) a narrowed `sovereignty`
block. [`../../contracts/provider-contract.md §8 (serve_data)`](../spec/contracts/provider-contract.md)
is the `information`-kind counterpart.

For the matching accreditation, see
[`../../registry/examples/accreditation-state-mn.yaml`](../../registry/examples/accreditation-state-mn.yaml)
— it attests `full-stack-sp`'s Container capability, narrowed to `realize_resources/Container` and scoped to
Minnesota (`US-MN`) sovereignty, showing how `subject_uuid`/`capability_uuid`/`scope` line up with the
declaration in A. (The provider *lifecycle* — how a declaration is registered and admitted — is documented in
[`../flows/provider-lifecycle.md`](../flows/provider-lifecycle.md).)

## 5. Where the gates run

Provider declarations are not repo artifacts — they are submitted at DCM registration
(`../flows/provider-lifecycle.md`), and every checklist row above is enforced there as an
admission check: an invalid declaration, an unresolvable standard token, a duplicate anchor
uuid, or an unparseable `supports` range refuses registration. What stays in-repo is the wire
shape itself (`registry/provider-adopted-standards.schema.json`) and the adoption register the
tokens resolve against; `tests/check_standards_registered.py` remains as a **report-only**
review aid (always exits `0`) listing prose standard citations with no register row.

# Profile resolution — the machine surface behind ADR-007

**What this settles:** ADR-007 decided *what a profile is* (a composed **set** with **floors**, built-ins immutable, **fork-on-modify**). This specifies the mechanics DCM runs against the profile record (`dcm-group.schema.json`, `group_class: policy_profile`, the `profile` block): how a profile **resolves** for a request, how two profiles **compare**, how they **compose**, and how a tenant **onboards** onto one. UDLM carries the record and defines these operations; DCM (Policy) executes them.

## 1. Resolution — which profile applies

For any request, the **applicable profile** is the **most-specific approved** profile in scope, else the applicable **default**:

1. Scope precedence (most specific wins): `resource_type` override → tenant → group → **platform default**. (Same precedence spine as policy domains, `policy-contract.md §4`.)
2. **Only `approved: true` profiles are selectable.** A custom (forked) profile is first-class but must be org-ratified before it can resolve — the "org ratifies" rule (`foundational-resources.md`). An unapproved profile is inert.
3. If nothing more specific is selected, the profile with `default: true` for that scope resolves.

Resolution is deterministic and auditable: the resolved profile uuid + version is recorded on the Requested record, alongside the `policy_results` it drove.

## 2. Comparison — set-containment over floors

Profiles are **sets, not levels**, so they are compared by **floor containment**, never by an ordinal:

> Profile **A satisfies** profile **B's** requirement **iff** A's *composed floor* ⊇ B's floor.

This is the one comparison operator the UCs need, and it answers all the "can this…" questions machine-checkably:
- **"Can this deployment meet the required profile?"** — the deployment's active profile floor ⊇ the required floor.
- **"Does a tenant restriction stay above the floor?"** (ADR-007 §2: restrict further, never below) — the restricted set ⊇ the profile floor. A restriction that drops a floor element is rejected.
- **"Is `sovereign` 'more than' `standard`?"** — *undefined and never asked*; they are distinct sets. Only containment is asked.

## 3. Composition — overlays union floors

Composing profiles (ADR-007 §1 overlays, e.g. a compliance overlay on a base profile) is **set union of floors + merge of operational config, more-restrictive-wins**:

- `composed.floor = ⋃ floor(p) for p in composed_from ∪ self`.
- `operational_config` merges with the more-restrictive value winning on conflict (a tighter approval ladder overrides a looser one).
- `required_mechanics` union — the deployment must provide the union of all composed profiles' mechanics.

A **compliance overlay** is therefore just a profile whose `composed_from` includes a base profile and whose own floor adds the compliance controls; resolution sees one composed floor.

## 4. Fork-on-modify

Any modification of a **built-in** (`is_builtin: true`) profile **produces a new custom profile** — a copy with `is_builtin: false` and `forked_from` set to the parent uuid. Resolution and composition never mutate a built-in; the built-in stays reproducible and referenceable. Approval (`approved`) is granted to the *fork*, not inherited.

## 5. Atomic tenant onboarding

Onboarding a tenant onto a profile is **all-or-nothing**. Creating the tenant (`group_class: tenant_boundary`) with a resolved profile atomically binds the profile's **floor** — its policies, its `required_mechanics` (attestation, time-sync capability, stores, retention), and the `store_bindings` the profile requires. The tenant is **not live until its profile floor is provisioned and operative**; a partial bind rolls back. This is why a profile declares *mechanics and data*, not just policy defaults (ADR-007 rejected policy-only): onboarding must be able to verify the whole floor is present before the tenant accepts requests.

## Boundary (ADR-008)

The `profile` record, the containment operator, and the composition rule are **UDLM** — a peer must resolve and compare profiles identically or two systems disagree on what a `sovereign` deployment guarantees. The onboarding transaction, the resolution engine, and provisioning the mechanics are **DCM**.

See ADR-007 (the decision), `dcm-group.schema.json` (the record), `policy-contract.md` (domain precedence + the policies a floor references), `governance/governance-matrix.md` (profile-bound defaults).

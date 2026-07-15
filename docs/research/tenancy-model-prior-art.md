# Research: multi-tenancy model — prior art & validation

**Type:** research note (decision support — not normative)
**Date:** 2026-07-14 · **Method:** assessed the UDLM/DCM tenancy surface against the deployed industry canon (SaaS isolation, Kubernetes multi-tenancy, data-isolation patterns, ReBAC, GDPR).
**Feeds:** `registry/dcm-group.schema.json` (the `tenant_boundary` model), DCM ADR-014 (RLS isolation), `foundations/data-model-core.md` §6 (the [D1] isolation ladder), `entities/resource-grouping.md` (tenant lifecycle + cross-tenant), `contracts/data-store-contracts.md` (tenant-context contract), `foundations/ownership-sharing-allocation.md`.

## What this settles

Before 1.0 locks the tenancy model, this checks it against how the industry actually does multi-tenancy — the same discipline applied to sovereignty. **Verdict: the model is fundamentally sound and, on isolation, exceeds the common baseline.** It independently reproduces the deployed canon — the silo/pool/bridge isolation taxonomy, RLS defense-in-depth, hierarchical tenants, ReBAC cross-tenant grants, per-tenant throttling, and staged offboarding are all present. Two minor refinements remain (data-erasure and per-tenant keys), parallel to the sovereignty gap-closures. Nothing here blocks 1.0.

## The model, in one line

A **Tenant is a DCMGroup** with `group_class: tenant_boundary` (`data-model-core §5`) — carrying an `isolation_level`, `nesting`, `ownership`, `quota`, `sovereignty_constraints`, and (via the `cross_tenant_authorization` class) scoped inter-tenant grants. DCM realizes isolation with PostgreSQL **Row-Level Security** (ADR-014). UDLM defines the isolation *contract*; the realization supplies the mechanism (the ADR-008 split).

## Model ↔ standards

| Standard / pattern | UDLM/DCM equivalent | Verdict |
|---|---|---|
| **AWS SaaS silo / pool / bridge** isolation strategies | `isolation_level` ladder — `shared_rls` (pool) → `schema_per_tenant` (bridge) → `database_per_tenant` (silo) → `store_per_tenant_zone` (silo + sovereignty), profile-keyed | **Exceeds** — a 4th sovereignty rung the SaaS canon lacks |
| **PostgreSQL Row-Level Security**, defense-in-depth | ADR-014 — RLS scopes every query at the DB, "not application logic"; `tenant_uuid` on every tenant-scoped table | Matches (textbook) |
| **Kubernetes hierarchical namespaces (HNC)** — org→team | DCMGroup `nesting` (org→dept→team), depth profile-governed, cycles rejected (GRP-INV-005/006) | Matches |
| **Google Zanzibar / ReBAC** cross-tenant sharing | `cross_tenant_authorization` group_class — a scoped, time-bound grant (granting/consuming tenant, authorized types, `expires_at`, purpose) + the §10 authorization lifecycle | Matches |
| **Noisy-neighbor control** — quota + throttling | `quota` (consumption ceiling) + `rate-limit-and-backpressure` `per_tenant` scope (runtime fairness) | Matches |
| **Tenant context propagation** (JWT claim → session → row filter) | `data-store-contracts`: "token claims → per-connection tenant binding → row filtering"; the isolation contract is UDLM, the mechanism is realization | Matches |
| **Tenant lifecycle / offboarding** | GRP-013 four-phase staged decommission (pre-validation → resource → membership → audit archival; children resolved first; **audit never destroyed**) | Matches |
| **Data residency per tenant** | `sovereignty_constraints` — a `tenant_boundary` structurally never spans a sovereignty boundary (GRP-012) | Matches |
| **Policy scoping by tenant** | policy domain precedence `system > platform > tenant > resource_type > entity` (ADR-014) | Matches |
| **ISO 27017 / CSA / SOC 2** tenant-isolation controls | the above, graded by profile (dev → sovereign) | Aligned |

## Why the model is right

- **Isolation is a first-class, per-tenant *dial*, not a platform-wide constant.** `isolation_level` lets one tenant sit on shared-RLS while another gets a dedicated database — the exact silo/pool/bridge flexibility the SaaS canon prescribes, keyed to the profile.
- **Isolation is enforced below the application.** RLS at the database is defense-in-depth — a code bug cannot leak cross-tenant, which is the property auditors actually want.
- **Cross-tenant is deny-by-default and explicit.** Sharing needs a `cross_tenant_authorization` grant (scoped, expiring) — never ambient — matching zero-trust and the ReBAC model.
- **Tenancy is structural, not advisory.** A tenant boundary cannot span a sovereignty boundary by construction (GRP-012), and offboarding is a defined four-phase sequence, not an ad-hoc delete.

## Two candidate gaps (minor; refinements, not blockers)

1. **Data erasure vs immutable audit (GDPR Art. 17 / 20).** GRP-013 correctly says *audit* records are never destroyed — but erasure/portability of tenant **payload data** at offboarding isn't explicit. The industry resolution is **crypto-shredding** (per-tenant keys; destroy the key to render data unrecoverable while the audit trail survives) plus a tenant **data-export** step. Recommendation: state, at GRP-013, that decommission erases (or exports on request) tenant data via crypto-shredding while preserving audit — squaring erasure with the immutable ledger.
2. **Per-tenant key isolation (BYOK).** The `sovereign` profile keeps key material in-boundary, but per-**tenant** keys aren't called out — and they are the enabler for gap 1's crypto-shredding and for BYOK, which regulated SaaS tenants routinely require. `store_per_tenant_zone` gets close. Recommendation: note per-tenant key isolation as the top rung's companion.

## Adopt, don't absorb

The model already speaks the right vocabulary — `isolation_level`, `tenant_boundary`, RLS, ReBAC-style grants — so this is validation, not adoption of new machinery. The two refinements are additive notes to `resource-grouping.md` (GRP-013) and the `data-model-core` §6 isolation ladder, not structural change. As with sovereignty: the spine is sound; close the edges.

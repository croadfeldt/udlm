# UDLM 1.0 — ADR Ratification Readiness

**Status:** 📋 Review artifact (decision-support for the maintainer). **Not** a status change — every
decision below remains `Proposed`; this is the assessment so ratification is a fast, informed pass.

**Why this exists:** 1.0 commits to backward compatibility and cannot ship on unratified decisions
(`UDLM-1.0-SCOPE.md` §5.1). All 11 prose ADRs (`docs/adr/`) and 9 JSON DecisionRecords
(`registry/instances/adr-*.json`) are `Proposed`. This ranks each **Ready** (exercised + settled, no
open question) vs **Hold** (a real open question or an unfinished dependency), so you accept the Ready
set in one review and defer the rest with eyes open.

Ratifying = flip `Status: Proposed → Accepted` (prose) / `state: PROPOSED → ACCEPTED` (JSON). Say the
word and I'll apply the greenlit set as a single reviewable PR.

## Prose ADRs (docs/adr/)

| ADR | Decision (gist) | Readiness | Note |
|---|---|---|---|
| 001 Topology type | failure/locality domains are data within a `Topology` type | **Ready** | Type exists + validates; the fault-domain modeling ADR-010 builds on it |
| 002 Capacity/utilization overlay | capacity is a *served observational overlay*, not a UDLM type | **Ready** | Consistent with the §8.1a capacity *advertisement* (shape) vs served utilization split |
| 003 Data mobility + process validation | reqs=data, mechanism=provider, permission=policy; process-validation lifecycle | **Ready** | Exercised by the rehydration / RTO UCs (rto/rpo in the mobility record) |
| 004 Provider capability declaration | generalize provider declaration into a capability declaration | **Ready (amended 2026-07-14)** | Was Hold — `topology_capability`/`operational_capability` were declared provider-wide; amended to scope all three capability blocks **per capability category** (ADR-PROV-002), matching `mobility` + §8.1a. Now consistent; schema not yet implemented (encodes the amended shape) |
| 005 Time integrity | ordering is structural/causal, not clock-based; time-sync is profile-scoped | **Ready** | Exercised by audit ordering; the dev vs fsi/sovereign time-sync floor now encodes it |
| 006 Convergence control model | re-entrant ECA loop; bounded convergence; idempotent | **Ready** | Core; exercised by idempotent-reconvergence, drift, recovery UCs |
| 007 Profile model | a profile is a composed *set* with a floor, not a level; fork-on-modify | **Ready** | Exercised by profile-resolution UC + now the 5 built-in profile instances (#73) |
| 008 UDLM/DCM boundary | the compatibility rule; what is UDLM vs DCM | **Ready** | Foundational; the whole 21-UC gap analysis rests on it |
| 009 Dependency fulfillment | DCM always orchestrates; per-constituent fulfillment; broker accommodation | **Ready** | Heavily exercised + refined this cycle; merged and stable |
| 010 Dependency-graph completion | SharedFaultDomain (derived), blast-radius, UnmetDependency | **Ready** | Exercised by the dependency-graph + dependency-failure UCs |
| 011 Validate-and-reserve | two-phase reserve → barrier → commit; TTL/expiry; stalemate | **Ready** | Settled this cycle end to end (contract + four-states + policy + events) |

**All 11 prose ADRs are Ready.** Each is exercised by at least one of the 21 UCs and carries no open
question I can find. Recommend ratifying the full set.

## JSON DecisionRecords (registry/instances/adr-*.json)

| Record | Decision (gist) | Readiness | Note |
|---|---|---|---|
| adr-udlm-dcm-boundary | UDLM = data model, DCM = realization | **Ready** | The JSON twin of prose ADR-008; ratify together |
| adr-resource-type-extension (PROV-004) | providers ADD via additive, portability-honest extensions; no override | **Superseded (ADR-038, #202)** | Deprecated: provider-specific data is a Provider-Class `SharedDataElement` (ADR-038); `provider_extensions` is the interim carrier until scoped classes land (#199), then removed (#202) |
| adr-provider-dispatch-role (PROV-001) | `data_role`; only `role: execution` crosses to a provider | **Ready** | Exercised this cycle (the two-phase data-scoping work); `data-roles.md` is its contract |
| adr-provider-capabilities-categories (PROV-002) | capability = (verb × domain); categories are the policy target | **Ready** | Underpins §8/capability-discovery; settled |
| adr-provider-capability-admission (PROV-003) | platform-admin admission disposition; default-deny | **Ready** | Settled; audit-record admission enum encodes it |
| adr-dcm-rbac-function-matrix (RBAC-001) | default (no-IdP) admin RBAC; function-capability matrix; default-deny | **Ready** | Schema (`function-capability-matrix.schema.json`) exists and validates |
| adr-cost-metering-placement | metering/billing is *referenced* by UDLM, not modeled | **Ready (off critical path)** | Decision is settled (adopt-by-reference); not required by the 21 UCs — ratify with the others or defer, low risk either way |
| adr-cost-metering-linkage (COST-002) | reciprocal cost/metering linkage hooks | **Hold (light)** | Its contract `cost-metering-linkage.md` is still Proposed; ratify once that contract settles. Not UC-blocking |
| adr-aep-alignment | adopt AEP; RFC 9457 for the error model | **Hold** | AEP conformance is an open workstream (#231) and `error-model.md` is still Draft; ratify after those close |

## Recommendation

- **Ratify now (18):** all 11 prose ADRs + udlm-dcm-boundary, PROV-001/002/003/004, RBAC-001, and
  (optionally) cost-metering-placement. These are exercised, settled, and carry no open question.
- **Hold (2):** `cost-metering-linkage` (until its contract settles) and `aep-alignment` (until AEP /
  error-model close). Neither blocks the 21 UCs or the surface-1.0 tag.

Ratifying the 18 clears exit-criterion §5.1 for everything the 21 UCs and the 1.0 surface depend on.

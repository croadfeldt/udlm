# UDLM 1.0 — Scope, Use-Case Coverage, and Exit Criteria

**Document Status:** ✅ Normative — the committed definition of the 1.0 release surface.
**What this settles:** what UDLM 1.0 *is* for the September release — the data/contract surface that
enables the 21 release use cases, what is deliberately **deferred**, the **exit criteria** that gate
the `0.1 → 1.0` tag, and the **profile posture** (implement against dev/eval; architect for
sovereign/fsi). It turns the scattered `P1–P7` gap references into one checkable definition.

UDLM is the **data / contract / type** layer. DCM is the orchestration/runtime. The boundary rule
(DCM ADR-008): *"could a peer implement this differently and still be valid? Yes → DCM; No → UDLM."*
Many use-case success criteria are satisfied by **DCM runtime** behavior over a UDLM shape — those are
called out below and are **not** 1.0 spec gaps.

---

## 1. The two completeness bars

- **Bar A — enable the 21 release use cases (data/contract layer).** Reached. After #69/#70/#71 and
  the 1.0-definition changes, exactly the concrete gaps below remained, and both are now closed:
  **tenant quota (P7)** and **override on the machine-validatable surface (P6)**. Everything else is
  covered or is DCM-runtime by the ADR-008 boundary.
- **Bar B — declare "UDLM 1.0" (ratified, backward-compat-committed).** A larger, mostly non-code bar:
  ratify the decisions, finish the load-bearing draft contracts, ship an executable conformance suite,
  and re-stamp `0.1 → 1.0`. Tracked in §5 (exit criteria) and §6 (deferred).

## 2. Profile posture — implement dev/eval, architect for sovereign/fsi

The architecture and wire contracts are **identical across profiles**; only the required *floor*
differs (DCM ADR-007 — a profile is a composed set with a floor, not a level). The five built-in
profiles are now defined as `policy_profile` records (`registry/instances/profile-*.yaml`), floors
nesting by set-containment (`docs/profile-resolution.md`):

| Profile | Role | Floor adds (over the one below) |
|---|---|---|
| **dev** (default) | **September implementation / evaluation target** | baseline: structural validation, tenant isolation, resolved-profile eval, append-only audit, four-state; causal-only time; no attestation |
| standard | baseline production | governance-matrix, recovery, drift reconciliation |
| prod | hardened production | blast-radius impact (ADR-010), dual-approval-destructive, bounded convergence |
| **fsi** | regulated (architected, not the impl target) | Merkle transparency audit, attestation-gated admission, override-approval, regulatory retention, attested time |
| **sovereign** | data-sovereignty (architected) | in-boundary key material (AUD-012), sovereign placement, sub-processor restriction |

September builds and validates the 21 UCs against **dev**; the sovereign/fsi floors exist so the
architecture is provably production-grade, not to be implemented first.

## 3. The 21 use cases → coverage (verified against merged `main`, not the stale DAV list)

Grouped by what enables them. "Covered" cites the merged spec; "DCM-runtime" = enabled by a UDLM shape
but executed by DCM (ADR-008).

| # | Use case (handle) | UDLM basis | Status |
|---|---|---|---|
| 1 | libvirt-vm-provider/vm-resource-representation | `compute.virtual-machine` 0.3.0; `realized-entity` | Covered |
| 2 | cross-domain/solution-architecture-deployment | `catalog-item` (constituents/bindings/fulfillment); realized receipt | Covered (DSL ingestion = DCM/Information-Provider) |
| 3 | compute/vm-standard-provision | profile-resolution; policy §7.7; universal-audit | Covered |
| 4 | compute/vm-intent-osac-placement | provider-contract §8 `realize_resources`; osac-better-together; provider provenance | Covered (placement algo = DCM ADR-019) |
| 5 | libvirt-vm-provider/vm-status-provenance | `realized-entity` field-level `provenance`/`status`/`drift` | Covered |
| 6 | data/persistent-volume-provision | `storage.volume`; tenancy; **quota** (now defined) | **Closed this release (P7)** |
| 7 | dcm-core/udlm-dependency-graph-data-model | edge kinds; ADR-010 fault-domain/blast-radius; graph-integrity | Covered |
| 8 | libvirt-vm-provider/cross-provider-dependency-ordering | graph-integrity DAG; ADR-009; ADR-011 reserve ordering | Covered (convergence = DCM ADR-006) |
| 9 | libvirt-vm-provider/dependency-failure-impact | ADR-010 `UnmetDependency` (blocking, blast_radius) | Covered |
| 10 | cross-domain/dynamic-rehydration | four-states §5 (replay intent, UUID preserved) | Covered (plan derivation = DCM) |
| 11 | compute/vm-provision-with-provider-failure | policy §13 recovery; four-states §2.5 conditions; ADR-011 release | Covered |
| 12 | observability/rehydration-rto-measurement | ADR-003 rto/rpo; realized snapshots | DCM/Observability-runtime |
| 13 | compute/idempotent-reconvergence | `generation`/`observed_generation`; four-states §3 | Covered (no-op decision = DCM ADR-006) |
| 14 | observability/drift-detection-remediation | four-states §6 drift record; policy §13 | Covered |
| 15 | governance/audit-merkle-tree-verification | universal-audit §8 (RFC 9162); AUD-012 key residency | Covered |
| 16 | governance/policy-override-approval | policy-contract §18; **`override` policy_type** (now on schema) | **Closed this release (P6)** |
| 17 | libvirt-vm-provider/provider-registration-capability | provider-contract §8.1a `resource_advertisement` (capacity) | Covered |
| 18 | cross-domain/provider-portable-rebuild | naturalization; portability + `bound_providers`; four-states §5.3 | Covered (re-resolution = DCM) |
| 19 | governance/policy-resolution-capability | policy-contract §7.7 three-state; profile-resolution | Covered |
| 20 | cross-domain/profile-resolution-capability | profile-resolution; `dcm-group` `policy_profile` + instances | Covered |
| 21 | governance/audit-chain-proofs-capability | universal-audit §8 (single-signer v1; witness = follow-up) | Covered |

**Net:** all 21 are enabled at the UDLM layer. The DAV roadmap's residual gaps for this set were
either stale (closed by ADR-010/§8.1a/realized-entity) or DCM-runtime.

## 4. September `P#` gap tracker — consolidated

| P# | Item | Status |
|---|---|---|
| P1 | VM enrichment (placement/networks/power) | ✅ `compute.virtual-machine` 0.3.0 |
| P2 | Profile schema | ✅ `dcm-group` `policy_profile` block |
| P3 | Provider capacity/inventory advertisement | ✅ provider-contract §8.1a `resource_advertisement` |
| P4 | Fault domains / SharedFaultDomain | ✅ ADR-010 |
| P5 | Blast-radius / redundancy / UnmetDependency | ✅ ADR-010 + `policy.schema` graph.* |
| P6 | Policy override (validatable surface) | ✅ `override` policy_type + allOf (this release) |
| P7 | Tenant quota (consumption) | ✅ `dcm-group` `quota` block + `quota.*` match sources (this release) |

## 5. Exit criteria to tag `udlm/1.0`

The surface is complete (§3–§4). Remaining before the tag (`VERSIONING.md` "Cutting the spec 0.1→1.0"):

1. **Ratify the decisions.** All 11 `docs/adr/` records and 9 `registry/instances/adr-*.json`
   DecisionRecords are `Proposed`; 1.0 commits to backward-compat and cannot ship on unratified
   decisions. **Ready to ratify** (settled, exercised by the 21 UCs): ADR-005, ADR-006, ADR-007,
   ADR-008, ADR-009, ADR-010, ADR-011, and the provider/boundary DecisionRecords (PROV-001/002/003,
   RBAC-001, udlm-dcm-boundary, resource-type-extension). Review-then-accept is the maintainer's call.
2. **Finish the load-bearing draft contract.** `contracts/schema-sharing.md` (Draft) defines the
   `/.well-known/udlm/schema-bundle` the conformance surface depends on — bring to Complete. The other
   drafts (`error-model`, `time-and-clock`, `retry-semantics`, `rate-limit-and-backpressure`) are
   triaged in §6.
3. **Executable conformance suite.** `VERSIONING.md` makes "the `CONFORMANCE.md` suite passes" the
   literal 1.0 gate; today CI runs only the registry validators. Building the §6 wire-conformance
   runner is **deferred** (§6) — until it exists, 1.0 cannot honestly claim the conformance bar.
4. **`0.1 → 1.0` re-stamp** — the mechanical procedure in `VERSIONING.md`; runs last, once 1–3 pass.

## 6. Explicitly deferred (out of 1.0 scope, tracked)

- **Executable conformance test runner** — large; overlaps DCM/test-infra. `CONFORMANCE.md` is Draft
  and `tests/test-framework-specification.md` specifies but does not implement it. Highest-value
  post-scope item; gates the honest 1.0 claim.
- **Draft contracts not load-bearing for the 21 UCs** — `error-model`, `time-and-clock`,
  `retry-semantics`, `rate-limit-and-backpressure`: finish or mark stable-by-reference before tag.
- **Per-type `stability` field** — coarse maturity signal while the spec is `0.x`; deferred candidate
  (`SPEC-DESIGN-REQUIREMENTS`).
- **Type completeness polish** — `Software.Service`, `Hardware.BMC`, `Hardware.BiosProfile` carry no
  `relationships` block; 4 types are `portability: partial`. Non-blocking for the 21 UCs.

## 7. The 1.0 surface (inventory)

38 resource types · 12 record schemas · 17 contracts (11 complete/stable, 6 draft — see §5/§6) ·
11 prose ADRs (001–011) + 9 JSON DecisionRecords · foundations/lifecycle/governance/design-principles
doc set · 5 built-in profiles. `conforms_to: udlm/0.1` on every type + schema today; the tag re-stamps
to `udlm/1.0` (§5.4).

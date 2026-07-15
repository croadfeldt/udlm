# UDLM ADR-021: The FSI profile — regulated (financial-services) production

**Status:** Accepted (maintainer decision, 2026-07-15)
**Date:** 2026-07-15
**Type:** Architecture Decision Record (a `DecisionRecord` with architecture scope — `entities/knowledge-family.md` §4.5)
**Related:** ADR-007 (profile model — distinct sets, not levels); ADR-020 (prod — the production floor this contains); ADR-005 (attested time); ADR-022/DCM (accreditation-gated admission); `observability/universal-audit.md` §8 (Merkle transparency, RFC 9162); `governance/accreditation-and-authorization-matrix.md` (two-gate verify-then-appraise); `contracts/policy-contract.md` §18 (override-approval); ADR-017 (per-profile-ADR template); the record: `registry/instances/profile-fsi.yaml`

> Owns the *rationale* for `fsi`; the floor data is the record's (single-source, SPEC-DESIGN §33).

## Context

Regulated institutions must be able to *prove* — to an auditor or regulator, after the fact — what happened, that it was authorized, and that the trust it rested on was real, not self-asserted. Hardened production (`prod`) contains the mistake; a regulated profile must additionally make the whole estate **evidentiary**.

## Decision

**`fsi` is the regulated financial-services profile.** It contains `prod`'s floor and adds the compliance dimension (see the record for the authoritative list): tamper-evident **Merkle-transparency audit** with inclusion/consistency proofs (universal-audit §8, RFC 9162); **attestation-gated, verifiable provider admission** — accreditation carries a proof chaining to a trust anchor, verified *before* its scope is appraised (the two-gate matrix §3.7/§3.8); **governance-matrix on every lifecycle operation** (no operation can scope out); the time-bounded **override-approval** workflow; **attested time**; and **regulatory retention**.

Per ADR-007, `fsi` differs from `prod` in *kind* (a compliance posture), not merely degree — it happens to contain `prod`'s floor but adds a regulatory dimension `prod` has no reason to carry. Target demographic: financial services and comparably regulated industries. It is **architected, not the September implementation target** — the architecture is production-grade, and September exercises it against the `dev` floor.

## Why these choices

- **Provable after the fact.** A signed, append-only Merkle log with inclusion/consistency proofs turns "our audit log says…" into "here is cryptographic evidence the log wasn't altered."
- **Trust must be verified, not claimed.** Attestation-gated admission with a *verifiable* accreditation (verify the signature, then appraise scope) stops a provider from self-asserting a compliance posture it can't prove.
- **No blind spots.** governance-matrix on *all* operations means no lifecycle action escapes boundary evaluation — the property a regulator asks for.
- **Attested time.** Ordering that must stand up in evidence needs an attested clock, not causal-only (ADR-005).
- **Floor is a minimum, not a filter** (ADR-007 §2): `fsi` mandates these; it does not *add* sovereignty confinement — that is `sovereign`. Nothing below is disabled; everything above stays available.

## Data · Policy · Provider (required lens — SPEC-DESIGN §29)

- **Data (UDLM):** `policy_profile` record, `is_builtin: true`, `approved: true`, `default: false`; the record names the Merkle-log, attested-time, accreditation, and retention mechanics the floor requires.
- **Policy (DCM):** governance-matrix evaluates every operation; override-approval is time-bounded and auditable; admission is gated on a verified accreditation.
- **Provider:** must present a **verifiable accreditation** (VC proof to a trust anchor) and satisfy the attested-time and Merkle-log mechanics; unaccredited providers are inadmissible.

## Consequences

- A named, referenceable regulated posture — an institution requires `fsi` by reference rather than re-deriving the control set.
- Onboarding an `fsi` instance requires the heavier mechanics operative before it serves (attested time, Merkle log, an accreditation authority) — the atomic floor check (`profile-resolution.md §5`) enforces it.
- The floor that `sovereign` further confines with in-boundary keys, sovereign placement, and sub-processor restriction.

## Options considered

- **(A) Treat `fsi` as "prod + more" on one severity scale.** Rejected: it differs in *kind* (compliance evidence + verified trust), not degree — ADR-007 profiles are sets, not levels.
- **(B) Leave regulatory controls to per-org overlays.** Rejected: the regulated control set is common enough to warrant a ratified built-in floor teams can require and be measured against.
- **(C) [chosen] prod's floor + Merkle-transparency audit + verifiable attestation-gated admission + all-operations governance + override-approval + attested time + regulatory retention.**

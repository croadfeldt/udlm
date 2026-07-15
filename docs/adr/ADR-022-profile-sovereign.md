# UDLM ADR-022: The Sovereign profile — data sovereignty (strictest floor)

**Status:** Accepted (maintainer decision, 2026-07-15)
**Date:** 2026-07-15
**Type:** Architecture Decision Record (a `DecisionRecord` with architecture scope — `entities/knowledge-family.md` §4.5)
**Related:** ADR-007 (profile model — distinct sets, not levels); ADR-021 (fsi — the regulated floor this contains); `observability/universal-audit.md` AUD-012 (in-boundary key material); `governance/accreditation-and-authorization-matrix.md` §3.8 (enforcement-plane attestation); ADR-022/DCM (sovereign accreditation, attested placement); ADR-017 (per-profile-ADR template); the record: `registry/instances/profile-sovereign.yaml`

> Owns the *rationale* for `sovereign`; the floor data is the record's (single-source, SPEC-DESIGN §33).

## Context

Sovereignty is not a stronger version of regulation — it is a *spatial* guarantee: the data, the keys that protect it, and the place it is realized must provably stay **inside a boundary** (a jurisdiction, a zone), attested by the party that enforces it, and reachable by no unauthorized sub-processor. `fsi` makes the estate evidentiary; `sovereign` additionally confines *where* it may exist.

## Decision

**`sovereign` is the data-sovereignty profile — the strictest built-in floor.** It contains `fsi`'s floor and adds the sovereignty dimension (see the record for the authoritative list): **in-boundary key material** (audit signing keys never leave the sovereignty boundary, AUD-012); **sovereign-only placement** (realization confined to authorized jurisdictions/zones, the sovereignty declaration *attested*, not self-asserted); **data-plane-attested residency** (data-at-rest residency conveyed to and attested by the enforcing provider — `enforcement_plane`, matrix §3.8); and **sub-processor restriction** (no data access by unauthorized sub-processors).

Per ADR-007 this is a distinct *kind* of set, not "fsi + a bit more": it adds spatial confinement, a concern `fsi` does not carry. Target demographic: workloads under data-residency / sovereignty mandates (public-sector, sovereign-cloud, data-localization regimes). It is **architected, not the September implementation target** — production-grade, exercised against `dev` in September.

## Why these choices

- **The boundary must hold for data *and* keys.** In-boundary key material (AUD-012) closes the gap where the data stays put but the keys that protect its audit trail don't.
- **Placement must be attested, not asserted.** Sovereign-only placement with an *attested* sovereignty declaration means a provider proves it realized inside the boundary — the enforcement plane attests residency (matrix §3.8), rather than the platform trusting a label.
- **No side doors.** Sub-processor restriction ensures the confinement isn't defeated by an unauthorized downstream processor.
- **Floor is a minimum, not a filter** (ADR-007 §2). `sovereign` is the strictest built-in, but the model is unchanged — a stricter or differently-shaped need is a *custom* profile forked from `sovereign`, not a new product surface.

## Data · Policy · Provider (required lens — SPEC-DESIGN §29)

- **Data (UDLM):** `policy_profile` record, `is_builtin: true`, `approved: true`, `default: false`; the record names the in-boundary-key, sovereign-attestation, data-plane-attested, and sub-processor mechanics.
- **Policy (DCM):** placement is confined to authorized zones; sovereignty declarations are verified as attested; sub-processor access is denied by default.
- **Provider:** must present a **sovereign accreditation** (attested, verifiable) and attest **data-plane residency** at the enforcement plane; a provider that cannot attest in-boundary realization is inadmissible.

## Consequences

- The reference posture for data-residency / sovereignty mandates; the strictest built-in floor and the natural fork-base for jurisdiction-specific custom profiles.
- Onboarding requires the sovereignty mechanics operative first (in-boundary keys, an attesting enforcement plane, sovereign accreditation) — enforced by the atomic floor check (`profile-resolution.md §5`).
- Completes the built-in set: `dev`/`homelab` (on-ramp) · `standard`/`prod` (production ladder) · `fsi`/`sovereign` (compliance + sovereignty).

## Options considered

- **(A) Model sovereignty as an `fsi` config toggle.** Rejected: it is a distinct guarantee (spatial confinement + in-boundary keys + attested placement), not a knob on the regulated floor — ADR-007 sets, not levels.
- **(B) One combined "regulated+sovereign" profile.** Rejected: many regulated estates are not sovereignty-bound; conflating them forces sovereignty controls on institutions that don't need them.
- **(C) [chosen] fsi's floor + in-boundary key material + sovereign-attested placement + data-plane-attested residency + sub-processor restriction.**

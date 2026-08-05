# Capability Discovery (folded into the Provider Contract)

**Folded 2026-07-23 into [`provider-contract.md`](provider-contract.md)** — the provider contract
owns capability documentation. Where the content lives now:

- The unified capability model (no provider types; closed verb vocabulary; verb × domain
  categories) — provider-contract §8 and §9 (decision: ADR-PROV-002).
- The registration wire shape — provider-contract §2 (this file's old §2.1 sketch was a stale
  fork: map-shaped capabilities, non-ISO sovereignty zones — the §2 shape is the one contract).
- Default-deny admission and the `effective_capabilities` ceiling — provider-contract §2
  (`dcm_registration_verdict`) + `PRV-009` (decision: ADR-PROV-003).
- The discovery wire protocol (advertisement endpoint, capability query, needs matching,
  invariants, `DISC-001..005`) — provider-contract §10.

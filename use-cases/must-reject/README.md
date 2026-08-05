# must-reject/ — the negative validation family

Every other family validates expressibility — that a claimed capability can be modeled and
gap-analyzed; this family validates governance discrimination — that an illegitimate intent is
correctly REFUSED. Success semantics are inverted: a use case here passes only if the system
rejects the request, and the refusal itself meets a contract — typed (machine-matchable error
class), actionable (names the remediation), non-leaking (the refusal discloses nothing the policy
protects, per the information-firewall behavior of ADR-041), and auditable (a refusal record
exists). One use case per rejection surface: tenancy boundary, sovereignty egress,
secrets-as-reference (Security.CredentialRef), binding-contract validation, provider
declare-and-select eligibility, and field-granular policy scope on projections.

**Where each surface's enforcement is specified.** The four-part refusal contract is stated once
in [`docs/spec/contracts/error-model.md`](../../docs/spec/contracts/error-model.md) §6a, with the error-path
non-disclosure rule in §8a and a surface-to-code index in §3.4. The per-surface mechanisms live
in their own homes: `XTA-006`/`XTA-007` (cross-tenant), `GMX-011` (sovereignty egress),
`GMX-012`/`GMX-013` (disclosed reduction and read/write scope symmetry), `CPX-013`/`CPX-014`
(credential material at intake), `CMP-009` (request-time binding re-resolution), and `PRV-011`
(the dispatch-boundary eligibility check). Two of these surfaced architectural questions rather
than gaps, drafted for ruling as ADR-049 (credential material at intent intake — the rejecting
path must not be where the secret lands) and ADR-050 (the absolute provider pin — whether a pin
may confer eligibility or only express preference).

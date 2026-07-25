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

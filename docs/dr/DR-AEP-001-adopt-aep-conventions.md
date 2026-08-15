# DR-AEP-001: Adopt AEP — RFC 9457 for the error model (UDLM), resource-oriented design + the Spectral linter for the API specs (DCM)

**Status:** Proposed
**Realized by:** _not yet_ — decided, no machine surface.
**Type:** Decision Record — a project/process decision (`docs/spec/foundations/knowledge-family.md` §4.5); architecture decisions are ADRs (`../adr/`)

**Background — read first (the cold reader's on-ramp; skip if you have the context).** The surfaces this decision governs: `docs/spec/contracts/error-model.md` · `design-
principles/adopted-standards.md` · `CONFORMANCE.md`

## Context

pkliczewski asked on dcm-project/udlm#18 (error-model:95) whether the error model should align
with AEP (aep.dev — the API Enhancement Proposals, the industry successor to Google's AIP).
Running the adopted-standards decision procedure (adopted-standards.md §1b): AEP-193 defines
its error model as IETF RFC 9457 (Problem Details for HTTP APIs) — a wide, stable, extensible
standard. UDLM's bespoke error envelope maps onto it cleanly: our closed error-code vocabulary
becomes the problem `type`, `message` splits into RFC 9457 `title`/`detail`, the audit link
becomes `instance`, and request_id/retryable/retry_after_seconds/timestamp/context become RFC
9457 extension members (which RFC 9457 §3.2 and AEP-193 explicitly sanction as top-level).
This is a Tier-2 record adoption and a step-3 CLEAN REPLACEMENT: RFC 9457 subsumes the
homegrown envelope, so we adopt it and RETIRE the bespoke shape — surface area goes down, not
up. The broader AEP (resource-oriented design AEP-121, the standard methods
Get/List/Create/Update/Delete, resource names, pagination) governs API SHAPE, which is DCM's
API specs (OpenAPI), not the UDLM data model — so it lands DCM-side, enforced by the AEP
Spectral OpenAPI linter (aep-dev/aep-openapi-linter). UDLM's field naming is already
snake_case and conforms. Grounded in producers/consumers: real consumers already parse the
error envelope (they gain a referenced standard instead of a bespoke one); real API clients
gain uniform resource semantics.

## Decision

Adopt AEP. (1) UDLM error model: adopt RFC 9457 (Problem Details) via AEP-193 as the error
envelope — `type` carries the closed error-code vocabulary, `title`/`detail` replace
`message`, `instance` carries the audit URN, and
request_id/retryable/retry_after_seconds/timestamp/context are RFC 9457 extension members; the
former bespoke envelope shape is retired. Declared as a Tier-2 adoption in adopted-
standards.md terms. (2) DCM API specs (follow-on, DCM repo): adopt AEP resource-oriented
design (AEP-121) and the standard methods, and wire the AEP Spectral OpenAPI linter (aep-
openapi-linter) into the API-spec CI. (3) UDLM field naming already conforms (snake_case).
This DR is the adoption record; the error-model.md change is its first execution.

## Data · Policy · Provider

- **Data** — The error envelope is DATA (a wire contract) — so RFC 9457 adoption lands in UDLM
(contracts/error-model.md). The closed error-code vocabulary and retryable semantics are
preserved as the problem `type` and extension members; only the shape is replaced. snake_case
field naming already conforms.
- **Policy** — No new policy — the retryable/retry semantics that drive retry/backoff policy
are unchanged; they move from bespoke fields to RFC 9457 extension members with identical
meaning.
- **Provider** — AEP resource-oriented design + standard methods shape the
provider/consumer/admin API surface, which is realization (DCM) concern — enforced by the AEP
Spectral OpenAPI linter in the DCM API-spec CI, not by the UDLM data model. UDLM keeps only
the wire DATA (the error envelope, entity/record schemas).

## Alternatives considered

- **Keep the bespoke UDLM error envelope** — a homegrown wire standard where a wide IETF one
(RFC 9457) cleanly fits; not net-negative; ignores the review ask *Rejected:* adopted-
standards §1b step 2/3 — a clean standard fit means adopt, don't keep a parallel bespoke form
- **Adopt the google.rpc.Status / ErrorInfo model (the older AIP shape)** — AEP-193 itself
moved to RFC 9457; adopting the superseded shape would diverge from current AEP *Rejected:*
AEP's current error model IS RFC 9457 — adopt what AEP actually specifies
- **Adopt AEP: RFC 9457 error envelope (UDLM) + resource-oriented API design & the Spectral
linter (DCM) (chosen)** — a wire-format change to the error envelope (acceptable pre-1.0;
error-model is Draft) and a DCM-side OpenAPI/linter effort to schedule

## Consequences

['contracts/error-model.md (RFC 9457 / AEP-193 error envelope)', 'design-principles/adopted-
standards.md (AEP/RFC-9457 as an adopted Tier-2 standard — reference)', 'DCM follow-on: AEP
resource-oriented OpenAPI conventions + aep-openapi-linter in CI']

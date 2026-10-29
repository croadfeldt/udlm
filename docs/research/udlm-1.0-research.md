# What "1.0" means for a specification — the research behind the lockdown plan

**Reference, not normative.** Fetched 2026-10-29 from primary sources, to define 1.0 for UDLM
(`registry/UDLM-1.0-LOCKDOWN.md` §2). Facts only; "not found" where a source is silent.

## The ten

### 1. Semantic Versioning 2.0.0
- **What 1.0 means:** "Version 1.0.0 defines the public API." Before it, "anything MAY change at any time."
- **The bar:** "If your software is being used in production, it should probably already be 1.0.0." No implementation, test or review bar.
- **Source:** https://semver.org/spec/v2.0.0.html

### 2. OpenTelemetry specification 1.0 (2021-02)
- **What stable meant:** every document marked stable or experimental; stable = Trace API/SDK, Context, Baggage. No backward-incompatible API change without a major; API majors supported three years after the next major; a signal is deprecated only once its replacement is stable.
- **The bar:** a signal becomes stable after "rigorous testing"; a compliance matrix (a checklist, not a test suite); language SDK release candidates alongside. Minimum candidate time: not found.
- **Deferred:** metrics, logs, semantic conventions.
- **Source:** https://github.com/open-telemetry/opentelemetry-specification/releases/tag/v1.0.0 ; https://opentelemetry.io/docs/specs/otel/versioning-and-stability/

### 3. CloudEvents 1.0 (CNCF, 2019-10)
- **What 1.0 meant:** core, primer and eight bindings tagged together; `specversion: 1.0`. No stated compatibility window or deprecation rule.
- **The bar:** 0.1 required at least two interoperating implementations and a blind interop demo; one release candidate, then a five-week verification period. Breaking renames were still made between 0.3 and 1.0.
- **Deferred:** adapters, SDK requirements, extensions stayed drafts.
- **Source:** https://github.com/cloudevents/spec/blob/v1.0/roadmap.md ; https://www.cncf.io/announcements/2019/10/28/serverless-specification-cloudevents-reaches-version-1-0/

### 4. OCI image-spec and runtime-spec 1.0 (2017-07), distribution-spec 1.0 (2021-05)
- **What 1.0 meant:** releases "should strive to be backward compatible"; distribution clients must support older registries. A hard "no breaking changes" sentence: not found.
- **The bar:** at least three release candidates a week apart, the count restarting on a breaking change (actual: six to seven); a one-week maintainer vote with published counts; distribution-spec shipped with a conformance suite and self-certification. Two years from formation to 1.0.
- **Deferred:** certification programme; the distribution spec itself (four more years).
- **Source:** https://github.com/opencontainers/image-spec/blob/main/RELEASES.md ; https://opencontainers.org/posts/announcements/2021-05-04-oci-dist-spec-v1/ ; https://github.com/opencontainers/distribution-spec/blob/main/conformance/README.md

### 5. FOCUS 1.0 (FinOps Foundation, 2024-06)
- **What 1.0 meant:** 43 columns "ready for general adoption". Version numbers "are not strictly representative of compatibility"; each change is classed compatible / migration-compatible / incompatible; removal needs one release as deprecated first.
- **The bar:** 0.5 → 1.0-preview → 1.0 in 14 months; candidate tags; consistency review, 30-day IP review, working-group approval, steering-committee ratification; four cloud providers shipped at GA. Columns were still renamed between preview and 1.0.
- **Deferred:** SaaS, PaaS, licensing, sustainability.
- **Source:** https://www.finops.org/insights/focus-1-0-available/ ; https://github.com/FinOps-Open-Cost-and-Usage-Spec/FOCUS_Spec/blob/working_draft/guidelines/contributors/spec-change-guidelines.md

### 6. Kubernetes API conventions (alpha / beta / GA)
- **What GA meant:** only compatible changes afterwards; an element added to a version is never removed from it; GA versions not removed within a major; beta deprecated within nine months or three releases.
- **The bar (KEP graduation):** alpha = behind a flag with e2e tests; beta = all functionality, security, monitoring and testing complete, feedback gathered; GA = real-world usage, installs, time for feedback, all beta gaps resolved. No fixed implementation count.
- **Source:** https://kubernetes.io/docs/reference/using-api/deprecation-policy/ ; https://github.com/kubernetes/enhancements/blob/master/keps/NNNN-kep-template/README.md

### 7. OpenAPI Specification 3.0.0 (2017-07)
- **What a version means:** major.minor is the feature set; patch fixes the document; tooling for 3.0 should accept every 3.0.x; minors must not break tooling built for a lower minor. 3.1 knowingly shipped a breaking change as a minor.
- **The bar:** three release candidates over five months, starting with an "implementer's draft" tool authors were asked to build against. Implementation count or conformance suite: not found.
- **Source:** https://spec.openapis.org/oas/v3.0.0.html ; https://www.openapis.org/blog/2017/07/26/the-oai-announces-the-openapi-specification-3-0-0

### 8. IETF standards track (RFC 2026, RFC 6410)
- **What each level means:** Proposed Standard is "immature"; Internet Standard has "a high degree of technical maturity". Changes come as a new RFC that obsoletes the old one.
- **The bar:** two independent, interoperable implementations from different code bases, for every feature; features without them are removed; at least six months as Proposed Standard; Internet Standard adds widespread deployment, no interoperability-breaking errata, and a four-week last call.
- **Source:** https://www.rfc-editor.org/rfc/rfc2026.html ; https://www.rfc-editor.org/rfc/rfc6410.html

### 9. W3C Recommendation track (Process, 2025-08)
- **What Recommendation means:** retains its status indefinitely; substantive corrections go through a 60-day review; new features need a new report unless the Recommendation allows them.
- **The bar:** Candidate Recommendation needs a plan for showing implementation experience, 28 days of review and wide review; features may be marked at risk and dropped; Recommendation needs "adequate implementation experience" (independent, interoperable, by people other than the authors, publicly deployed), all issues addressed, and a 28-day Advisory Committee review.
- **Source:** https://www.w3.org/policies/process/

### 10. Kubernetes Gateway API 1.0 (2023-10)
- **What GA meant:** Gateway, GatewayClass and HTTPRoute stable on the standard channel; no breaking changes, only loosened validation; the experimental channel may break at any time.
- **The bar:** full conformance test coverage, multiple conformant implementations, widespread use, six months as alpha, no significant change for one minor release and three months, owner approval. Four years from first release.
- **Deferred:** other route kinds, timeouts, backend TLS.
- **Source:** https://github.com/kubernetes-sigs/gateway-api/releases/tag/v1.0.0 ; https://gateway-api.sigs.k8s.io/docs/concepts/versioning/

## Patterns (out of the nine concrete specs)

1. 1.0 is a compatibility promise, not a completeness claim: 8 of 9 shipped with named parts left out.
2. Stability is declared per component: 7 of 9.
3. Independent implementations are the commonest gate, "two" the floor where a number is given: 5 of 9 state it; all 9 had more than one implementer at 1.0.
4. A conformance or test suite was an explicit gate: 3 of 9.
5. A named candidate stage with a minimum hold: 8 of 9; 6 state the hold in days or months.
6. A recorded governance vote closed it: 7 of 9.
7. Breaking changes were still made inside the final candidate run: 3 of 9.
8. A post-1.0 support window stated in time: 2 of 9 (OTel three years, Kubernetes within a major).
9. Explicit deprecation rules: 6 of 10.
10. Two bodies bent semver for adopters' sake (OpenAPI 3.1, FOCUS).
11. First draft to 1.0: 14 months to four years.
12. Nobody promises compatibility across majors: 9 of 9.

# How specifications graduate a part from experimental to stable — the research behind UDLM's ladder

**Reference, not normative.** Fetched 2026-11-03 from the process documents. The ladder it informed
is `docs/spec/governance/graduation.md`.

## The CNCF, first

The CNCF's ladder is for a project, not a feature: Sandbox, Incubating, Graduated.

- **Sandbox** is eligibility paperwork: Apache-2.0 licence, a MAINTAINERS file, a security policy, a
  roadmap, a contributing guide, a code of conduct, separation from any product, and a description
  of the spec if the project is one. Breaking changes are expected.
- **Incubating** asks for discoverable governance, a maintainer lifecycle, a contributor ladder, a
  public roadmap, a documented release process, and a security reporting process with
  self-assessment. It also asks for an OpenSSF Best Practices passing badge, a public adopters list
  with at least three independent adopters, and five to seven adopter interviews. For a spec: known
  implementations, the change process for normative content, and conformance or interoperability
  testing.
- **Graduated** adds maintainers from at least two organizations, a contributor ladder that has
  produced them, a release document, a third-party security review, production adopters, and for
  a spec the conformance results across implementations.
- The CNCF does not prescribe a feature-maturity scheme for a hosted spec; it asks the project to
  describe its own.
- Decided by a two-thirds vote of the TOC after sponsor due diligence and a two-week public comment.

Sources: https://github.com/cncf/toc/blob/main/process/README.md ·
https://github.com/cncf/sandbox/blob/main/README.md ·
https://github.com/cncf/toc/blob/main/.github/ISSUE_TEMPLATE/template-incubation-application.md ·
https://github.com/cncf/toc/blob/main/.github/ISSUE_TEMPLATE/template-graduation-application.md

## Ten per-feature ladders

| Body | Stages | What moves a part up | Soak | Who decides |
|---|---|---|---|---|
| Kubernetes API | alpha, beta, GA | beta: all functionality, security, monitoring and tests complete, API review; GA: real-world use, installs, time for feedback, conformance tests approved by SIG Architecture | beta bounded at 9 months or 3 releases | SIG leads, production-readiness approvers |
| Gateway API | experimental, standard | full conformance test coverage; multiple conformant implementations; widespread use; 6 months as alpha; no significant change for 1 minor release and 3 months | 6 months + 3 months | subproject owners and KEP reviewers |
| OpenTelemetry | development, alpha, beta, release candidate, stable | described per stage (beta: prior production exposure; RC: feature-complete); "rigorous testing" to stable | none for moving up; deprecated kept 6 months | SIG maintainers |
| TC39 | 0, 1, 2, 2.7, 3, 4 | 2.7: complete spec text, reviewer and editor sign-off; 3: tests and pre-implementation experience; 4: two implementations passing Test262, field experience, editor sign-off | none | committee consensus |
| Rust | unstable, stable | a stabilization report: tests and coverage, docs in the Reference, unresolved questions answered; team sign-off | 10-day final comment period | lang team |
| W3C (CSS WG) | WD, CR, REC | two independent interoperable implementations of each feature, passing the test suite; at-risk features may be dropped | 6 months in CR; 28-day reviews | working group, then the W3C Decision |
| IETF | Proposed Standard, Internet Standard | two independent interoperating implementations with widespread deployment; no interop-breaking errata; no unused complex features | 4-week last call | IESG |
| Python | provisional, final | package stability and developer support, judged per case | one feature release | core developers |
| OpenFeature | experimental, hardening, stable | not stated; the TSC approves graduation of documents | none | TSC |
| CloudEvents | working draft, release candidate, released | extensions need two voting members' support before entering the core; release needs a final review | one week per vote | one vote per company, majority |

Sources: the Kubernetes KEP template and API deprecation policy; https://gateway-api.sigs.k8s.io/concepts/versioning/ ;
https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/maturity-levels.md ;
https://tc39.es/process-document/ ; https://rustc-dev-guide.rust-lang.org/stabilization-guide.html ;
https://www.w3.org/policies/process/ and https://www.w3.org/TR/css-grid-1/ ;
https://www.rfc-editor.org/rfc/rfc6410 ; https://peps.python.org/pep-0411/ ;
https://github.com/open-feature/spec/blob/main/specification/README.md ;
https://github.com/cloudevents/spec/blob/main/docs/GOVERNANCE.md

## Patterns

1. A named body signs off: 10 of 10.
2. Tests or a conformance suite per feature: 5 of 10.
3. A deprecation guarantee once stable: 5 of 10.
4. Independent implementations, two as the floor: 4 of 10.
5. Real-world use before stable: 4 of 10.
6. A minimum soak time: 4 of 10.
7. An explicit no-breaking-change window: 2 of 10 (Gateway API: one minor release and three months).
8. The ladders with the fewest stages carry the most concrete, numeric criteria; the longest ladders
   describe expectations and state a threshold only at the last step, or not at all.
9. The three bodies that judge per feature (W3C, IETF, Gateway API) all pair two independent
   implementations with a test per feature.

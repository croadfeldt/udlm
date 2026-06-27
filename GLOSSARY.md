# UDLM Glossary

Defines the load-bearing terms used across the UDLM specification, so readers (and
conformance reviewers) share one vocabulary. Where a term is overloaded in common usage,
this glossary states the **single sense UDLM means**.

| Term | Definition |
|---|---|
| **UDLM** | Universal Data Lifecycle Model — a vendor-neutral **data substrate** (Apache-2.0) that specifies how data is modeled and moved through its lifecycle (Intent → Requested → Realized → Discovered). UDLM is a *specification*, not an implementation. |
| **realization** | A system that **implements UDLM's interfaces** so its data is wire-compatible with other realizations. UDLM is **realization-neutral**: its definition, validation, and use depend on no specific realization. DCM and DAV (below) are example realizations. |
| **substrate** | The shared, realization-neutral foundation every realization implements — the meta-schema, the `contracts/` interface specs, the four-state lifecycle, and the identifier scheme. "Wire-compatible substrate" = this common layer, which lets independent realizations exchange data **without per-realization adapters**. |
| **wire-compatible** / **wire-level interoperability** | Any conformant peer can deserialize, scope-resolve, reference, and validate another peer's data. Peers conformant to the same SPEC **MAJOR** interoperate without adapters (CONFORMANCE.md §9). |
| **contract** | UDLM uses this word in **one** sense only: the normative **interface specifications under `contracts/`** (wire contracts, provider contract, policy contract). For the generic notion "obligations a party must satisfy," this spec prefers **"interface"** or **"specification"** to avoid overloading. |
| **surface** | A named, externally-observable interface area (e.g., consumer API, provider callbacks, federation, audit export). The **conformance surface** is what an independent verifier tests. |
| **naturalization / denaturalization** | The adapter operation a provider performs: **naturalize** = translate a native (vendor) representation *into* the unified data model; **denaturalize** = translate the realized state *back out* to the native form. |
| **profile** | A named conformance bundle (e.g., `minimal`, `prod`) selecting which optional surfaces/behaviors a realization supports. Two peers may both be conformant yet run different profiles. |
| **decision_gravity** | A governance weight on a request/decision (`none` | `routine` | …) indicating how much scrutiny/authority it warrants (design-principles/design-priorities.md). |
| **leap-second smear** ("smear") | A clock strategy for absorbing leap seconds gradually rather than as a 1-second step; a conformance-declared time behavior (CONFORMANCE.md time section). |
| **concern_type** | A Policy Group artifact classifier (e.g., `data_authorization_boundary`) naming which governance concern a policy matrix addresses. |
| **DCM** | Data Center Manager — the example realization of the **Resource** (infrastructure) family. **Non-normative** with respect to this spec: UDLM is realization-neutral; DCM is the primary driver but is not required to define, validate, or use UDLM. |
| **DAV** | An open-source architecture-assessment tool, cited in this spec **only as a non-normative example realization** of the **Knowledge** family (the peer demonstration to DCM's Resource family — see `docs/case-study-dav-knowledge-realization.md`). **Nothing in UDLM's definition, validation, or use depends on DAV.** It is illustrative, included to show UDLM holds outside infrastructure. |

> **Realization-neutrality (normative):** UDLM is defined, validated, and used independently
> of any realization. Where DCM or DAV are named, they are **examples**, never requirements.

# UDLM ADR-035: Reference-vocabulary portability and provider advertisement

**Status:** Accepted (croadfeldt upstream) — an application of ADR-037 (PVD)
**Date:** 2026-07-21
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)
**Related:** ADR-012 (data-references — the in-field reference shape); ADR-004 (provider capability declaration);
ADR-023 (host networking as data / naturalization); ADR-024 (filling provider-required inputs); ADR-037 (the PVD
family this applies); core-tenets **T5** (adopt standards by reference); layering-and-versioning §3.7
(reference-data kinds)

## Context
`data_reference` (ADR-012) lets a field point at a governed `reference_data` layer instead of inlining a value,
and §3.7 pre-enumerates the reference kinds — `os_image`, `storage_class`, `vm_size`, `network_zone`,
`gpu_profile`, `location`, `topology_capability`, `environment`. The mechanism guarantees referential
**integrity**: a dangling ref, a type mismatch, or a wrong advisory name is a hard failure.

Integrity is not **portability**. Two providers can each advertise an `os_image` vocabulary using different
identifiers (`rhel-9` vs `RHEL9.0`), and nothing requires their advertised sets to align to a shared vocabulary
or to be discoverable at all. So converting a free string (e.g. `guest_os`, PVD-001) to a `data_reference` fixes
the *shape* but can still leave a portable pointer to non-portable names. Three things must be true for a
referenced value to be portable, and today only the first is specified.

## Decision
For any reference kind whose vocabulary must **federate across providers**:

1. **Portable identity (UDLM, T5).** The kind adopts a standard for its *identity* — a Tier-1 codelist. OS →
   **CPE 2.3** or **os-release** (`ID` / `VERSION_ID`). The `reference_data` layer's identity conforms to it;
   provider-native names are **naturalized** to that identity at the provider edge (ADR-023), never leaked raw.
2. **Advertised eligibility (UDLM contract → provider data).** Each provider advertises the subset it realizes
   via capability discovery (ADR-004): the provider support matrix carries *which* `os_image` / `storage_class`
   / `vm_size` identities it offers.
3. **Validated membership (DCM / Policy).** At request, DCM validates the declared reference ∈
   *(portable vocabulary ∩ provider-advertised set)*; a miss is a placement/validation finding (ADR-024).
   Selection is *from the advertised set*, never a guessed string.

**Boundary (peer test, ADR-008).** The reference *kind*, the *adopted identity standard*, and the *obligation to
advertise* are substrate invariants a peer must honor to interoperate → **UDLM**. Negotiating, matching, and
validating membership are realization choices → **DCM**.

## Data · Policy · Provider (SPEC-DESIGN §29)
- **Data** — the `reference_data` vocabulary + its adopted identity; the provider's advertised set (capability data).
- **Policy** — DCM validates membership and gates a non-portable inline value.
- **Provider** — advertises its eligible subset; naturalizes native names to the portable identity.

## Options considered
- **(A)** Free string. *Rejected* — the PVD-001 finding.
- **(B)** `data_reference` with no identity standard. *Rejected* — a portable pointer to non-portable names;
  integrity without cross-provider meaning.
- **(C) [chosen]** `data_reference` + adopted portable identity + advertised eligibility + validated membership.

## Consequences
- Needs an `os_image` vocabulary and an adopted OS-identity standard registered (`adopted-standards.md`).
- `storage_class`, `vm_size`, `gpu_profile`, a new `zone` kind follow the identical three-part loop.
- The PVD gate (ADR-037) enforces that new selectable fields adopt this loop rather than regressing to a string.

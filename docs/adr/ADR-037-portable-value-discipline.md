# UDLM ADR-037: Portable-value discipline (PVD)

**Status:** Accepted (croadfeldt upstream)
**Date:** 2026-07-21
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)
**Related:** ADR-035 / ADR-036 (the two mechanisms this gate points at); ADR-012 (data-references); ADR-028
(rule-ID naming + registry); core-tenets **T5** (adopt outward) / **T7** (reduce inward); `check_single_source.py`
+ SPEC-DESIGN §33 (the single-source precedent this mirrors). **Home of the `PVD` rule family:**
`design-principles/portable-values.md`.

## Context
The review surfaced **two faces of the same discipline breach — a portable value restated inline instead of
referenced.** (1) `guest_os` and `storage_class` were free strings where §3.7 *already* sanctioned a reference
kind; a sweep found several more across the registry. (2) A VM `networks[]` block carried an `ip_mode` /
`address_config` shape that re-expressed `Network.IPAddress.allocation` + `address` — the RFC 8344/NMState form
UDLM already adopts (ADR-023) — inline, a pure T5/T7 breach with no free string in sight. Nothing catches either:
there is no check for "a selectable value as an unconstrained string" or for "an adopted-standard/typed shape
re-expressed inline," so both re-enter with every new type. Single-source and settled-vocabulary are held to
account exactly the way this should be — a **rule + an automated check + a review-sweep line** — and this
discipline is load-bearing for portability.

## Decision
1. **The rules — one family, two findings** (defined in `design-principles/portable-values.md`, the `PVD` home):
   - **PVD-001 (free-string vocabulary).** A selectable value MUST be a `data_reference` to a reference-data kind
     (ADR-012/035), a bounded **codelist** (T5), or a **requirements descriptor** (ADR-036) — never an
     unconstrained string.
   - **PVD-002 (inline re-expression).** A field MUST NOT restate, inline, an **adopted standard's body**
     (adopt by reference — T5) or the **shape of a referenceable resource type** (bind by an ADR-025 reference —
     T7).
2. **Home + family.** `design-principles/portable-values.md` is the `PVD` family's home; the prefix is registered
   in `registry/rule-id-registry.yaml` (ADR-028). PVD is the third sibling of T5 (adopt *outward*) and T7 (reduce
   *inward*): **reference what the model already owns, don't restate it inline.**
3. **The automated check.** `tests/check_portable_values.py`, CI-wired like `check_single_source.py`, enforces
   both rules — PVD-001 hard-fails; PVD-002 runs as a review-flag until its overlap catalogue is tuned. It scans
   type specs **and** instances, layer-contributed `fields`, and examples (the discipline holds in *data*, not
   just definitions).
4. **The sweep line.** Added to CONTRIBUTING "review sweep" + SPEC-DESIGN-REQUIREMENTS:
   *"Portable-value discipline — reference what the model already owns: a selectable value is a reference,
   codelist, or requirement, never a free string (PVD-001); an adopted-standard/typed shape is bound by
   reference, never restated inline (PVD-002)."*

## Data · Policy · Provider
- **Data** — the rules constrain how portable *data* is shaped.
- **Policy** — CI (the check) is the enforcement; per-request validation lives in ADR-035/036.
- **Provider** — the discipline is what makes provider-advertised vocabularies and adopted-standard bodies
  portable across providers.

## Options considered
- **(A)** Prose guidance in SPEC-DESIGN only. *Rejected* — un-enforced guidance re-enters per PR.
- **(B)** PVD-001 only (strings), leave inline re-expression to review. *Rejected* — a re-expression breach had
  no string to catch and slipped through anyway.
- **(C) [chosen]** The PVD family (001 + 002) + one automated check + one sweep line — the single-source model.

## Consequences
- The sweep backlog becomes the first PVD fix-PRs (ISA codelist; `instance_size` codelist; VM `placement.zone`).
- ADR-038 (the scoped-Class paradigm) is the model these apply *under*, and generalizes them: *one canonical
  mechanism & notation*, and *reference-discipline in data, not just definitions*.

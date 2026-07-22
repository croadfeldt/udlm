# Portable-value discipline (PVD)

The home of the **PVD** rule family (ADR-037). A sibling of the outward/inward tenets — **T5** (adopt external
standards by reference, don't re-express) and **T7** (reduce to an existing mechanism) — aimed at *how a
portable value is shaped*: **reference what the model already owns; don't restate it inline.** Whether the
"what" is a *vocabulary* (PVD-001) or a *standard/type shape* (PVD-002), a value that a provider naturalizes or
that must federate across providers is not written as a free string or an inline copy.

This discipline is load-bearing for portability — the project's reason to exist — so it is enforced, not
advised: a violation is a **review finding** and, where mechanically detectable, a CI failure
(`tests/check_portable_values.py`).

## Rules

| Rule | Statement |
|---|---|
| `PVD-001` | **Free-string vocabulary is a finding.** A value chosen from a set — provider-advertised, standardized, or requirement-satisfiable — MUST be one of: a `data_reference` to a `reference_data` kind (ADR-012; layering §3.7); a bounded **codelist** (`enum`, or an adopted-standard codelist, T5); or a **requirements descriptor** the provider matches. An unconstrained string for such a value is non-conformant. *Out of scope (legitimately free):* human names/descriptions/handles; opaque provider-reported ids in `outputs` / discovered state; values already constrained to an adopted format (FQDN/RFC 1035, CPE). |
| `PVD-002` | **Inline re-expression is a finding.** A field MUST NOT restate, inline, the body of an **adopted standard** (adopt it by reference — T5) or the **shape of a referenceable resource type** (bind it by an ADR-025 reference / relationship edge — T7). Duplicating a shape the model already owns is non-conformant even when no free string is present. |

## Selection rule (which of the three, for PVD-001)

- **Reference** — when the vocabulary is itself portable: a first-class type/catalog the provider advertises, whose *identity* is portable (e.g. `os_image` keyed to an adopted OS-identity standard, ADR-035).
- **Requirement** — when the candidate set is inherently **vendor-native** (storage classes: `Platform.StorageClass` adopts Kubernetes and does not port). State the requirements (tier / IOPS / durability / …); the provider matches; the chosen native class is a realized fact, never portable intent (ADR-036).
- **Codelist** — for a small, neutral, bounded set (`enum`, or an adopted Tier-1 codelist).

Do not default to "reference": a reference to a *non-portable* type just relocates the leak — that is the trap
PVD catches.

## Enforcement

- **Automated** — `tests/check_portable_values.py` flags (a) a `spec` string field matching a vocabulary signal
  without enum/reference/requirements (PVD-001), and (b) a `spec` object whose field-set substantially overlaps
  an adopted-standard body or a referenceable type's shape (PVD-002, review-flag). It scans type specs **and**
  instances, layer-contributed `fields`, and examples (the discipline holds in *data*, not just definitions).
- **Judgment** — the review sweep checks the same, plus the generalizations recorded in ADR-038: *one canonical
  mechanism & notation* (no parallel selector/filter/query construct; identity dotted, address/selector URL),
  and *reference-discipline in data, not just definitions*.

Related: ADR-035 (reference-vocabulary portability), ADR-036 (storage requirements), ADR-037 (this family's DR),
ADR-038 (the scoped-Class paradigm these apply under), core-tenets T5/T7.

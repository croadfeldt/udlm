# Authoring a governed vocabulary (reference data)

**What this is.** The procedure for adding a **reference-data vocabulary** — a governed, shared set of terms
that many records point at instead of inlining a copy: storage tiers, OS images, network zones, GPU profiles.
Each term is a `layer` record; the vocabulary is the set of them. You author the terms and their curation;
DCM resolves references and injects the data at render time.

> **Read once first:** [`../../CONTRIBUTING.md`](../../CONTRIBUTING.md) and [`README.md`](README.md) (the
> universal contract).

## 1. When to use — and when not

Author reference data when a **selectable value should be one governed source of truth**, not a string
retyped per record. The discipline behind that is **ADR-037 / PVD-001 — a selectable value is a
`data_reference`, a bounded codelist, or a requirements descriptor; never a free string and never an inline
re-expression of a native value.** A vocabulary is the *reference* arm of that rule.

**When *not* to — pick the right arm (ADR-036 is the discriminator):**

- The candidate set is **inherently vendor-native** (storage classes, CSI provisioners). Then the portable
  value is a **requirements descriptor**, not a reference — **ADR-036: storage selection is
  name-selectable but requirements-authoritative; a `tier` term denotes a requirements floor (its minima),
  and the chosen native class is recorded as a realized output, never as intent.** Note the nuance: the
  *tier vocabulary itself* is authored as reference data (below), but an instance selects by the neutral tier
  name or by explicit minima — it never references a native class.
- The value is a small fixed neutral enum with no per-term metadata — a **codelist** is lighter than a
  vocabulary.
- You are deciding *what to do* about a value — that is a **policy** ([`policy.md`](policy.md)), not data.

## 2. The steps, in order

1. **Write one term per record** at `registry/examples/<vocab>-<term>.yaml`. Each is a `layer`
   (`layer.schema.json` `required`): `record_type: layer`, a fresh v4 `uuid`, `conforms_to: udlm/0.1`,
   `name`, `version`, `tenant_uuid`, `layer_type: reference_data`, and `fields`.
2. **Set `reference_data_type`** — **required when `layer_type` is `reference_data`** (the schema's `allOf`
   enforces it). This is the *match axis*: **ADR-012 — a `data_reference` is `{ref_uuid (authoritative),
   ref_name (advisory), reference_data_type}`, and it resolves only to an *active* reference-data layer of the
   *same* `reference_data_type`; the type stops a field binding a `network_zone` where an `os_image` was
   meant.** Use a stable snake_case token (`storage_tier`, `os_image`, `network_zone`).
3. **Put the governed content in `fields`** — a **named requirements bundle, not a bare enum value.** A
   storage tier is not the string `"performance"`; it is `{tier_code, min_iops, min_throughput_mbps,
   description}` — the shared SLA floor the name *means*. That bundle is exactly what makes the vocabulary
   portable and requirements-authoritative (ADR-036).
4. **Set governance** — `domain` (usually `platform` for a shared vocabulary), and `contributor`
   (`contributor_type` + `review`, e.g. `dual_approval` for a platform vocabulary that flows through the
   GitOps PR model).
5. **Curate the term proposed → canonical.** A vocabulary value enters staged: **ADR-039 — a value enters as
   `proposed` (a dirty-safe holding pen), and `canonical` is the promoted, portable set; reference resolution
   honors the distinction so a strict profile can require canonical vocabulary. Cleaning *is* lineage — dedupe
   and rename are `supersede` operations (ADR-012), never deletion.** The `proposed → under-review →
   canonical → deprecated` lifecycle (`docs/spec/foundations/four-states.md`) is the value-level curation state; a
   revision of a canonical term is a **new immutable record** that names its predecessor via `supersedes`,
   never an edit (ADR-012 §6, ADR-051). (The `layer` record's own `status.state` — `active`/`deprecated`/
   `retired` — is the record lifecycle; the proposed/canonical stage is the vocabulary-intake curation the
   intake ladder in [`../design/vocabulary-intake-ladder.md`](../design/vocabulary-intake-ladder.md) operates.)

## 3. Completeness checklist — and the gate that enforces each

| Ships with the vocabulary term | Why | Gate |
|---|---|---|
| Validates against `layer.schema.json` (required fields; `reference_data_type` present) | Valid by construction | `registry/tools/validate.py` |
| Every `data_reference` to this vocabulary resolves — active target, matching type, honest `ref_name` | Referential integrity (ADR-012 `check_data_references`) | `registry/tools/validate.py` |
| Each `supersedes` uuid resolves to a same-type layer at a strictly lower version | Lineage integrity (`check_layer_lineage`) | `registry/tools/validate.py` |
| Fresh `uuid`; a revision is a new record, never an in-place edit | Immutable-record family (ADR-051) | `registry/tools/validate.py`, `tests/check_identity_integrity.py` |
| Any normative rule the vocabulary doc introduces uses a registered, single-home prefix | One definition per rule (ADR-028) | `tests/check_single_source.py` |

## 4. A worked pointer

Copy
[`../../registry/examples/example-reference-data-storage-tier.yaml`](../../registry/examples/example-reference-data-storage-tier.yaml)
— the `performance` term of the `storage_tier` vocabulary: a `layer` with `layer_type: reference_data`,
`reference_data_type: storage_tier`, `contributor.review: dual_approval`, and `fields: {tier_code: performance,
min_iops: 20000, min_throughput_mbps: 500, description: …}`. It is the canonical illustration of the rule in
step 3 — the term *is* its requirements floor, not a string. For lineage, the standing pattern is
`example-reference-data-network-zone.yaml` + its `-v2.yaml` (a new immutable version that `supersedes` v1) —
see ADR-012 §"Consequences". How the vocabulary is consumed and requirements-matched end to end is walked in
[`../flows/storage-provisioning-lifecycle.md`](../flows/storage-provisioning-lifecycle.md).

## 5. Run the gates

From the repo root:

```console
$ python registry/tools/validate.py
...
ALL VALID — 0 invalid

$ python tests/check_single_source.py
rule-id single-source: 46 registered prefix(es); 400 rule IDs across the normative surface; 0 collide (0 baselined); 2 sanctioned co-home(s), 0 spread-debt entr(y/ies).
OK — every rule-ID prefix is registered; every ID has a single definition.
```

Both exit `0`. `validate.py` runs `check_data_references` and `check_layer_lineage` as part of the sweep and
prints an advisory change-impact section (which references are pinned to a superseded version) before the
`ALL VALID — 0 invalid` verdict — that section is informational, not a failure. A dangling, mistyped, or
dishonestly-named reference fails the run and names the offending record.

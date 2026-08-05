# UDLM Rule-ID Naming Convention

**Document Status:** ✅ Complete — normative
**Decision record:** [ADR-028 — rule-ID naming and registry](../docs/adr/ADR-028-rule-id-naming-and-registry.md)
**Registry:** [`rule-id-registry.yaml`](rule-id-registry.yaml) (schema: [`rule-id-registry.schema.json`](rule-id-registry.schema.json))
**Enforced by:** `tests/check_single_source.py` (CI)

Every normative rule in the UDLM spec carries a **stable ID** so a doc, a review, or a peer can
cite one rule and land on exactly one definition. This document is the convention those IDs
follow; the registry is where every prefix is recorded.

## 1. Form

```
PREFIX-NNN            ENT-006, PRV-009, DPO-003
PREFIX-SUB-NNN        REG-DP-002        (a hyphen-segmented sub-series; leading prefix is REG)
```

- **`PREFIX`** — 2–6 chars, `^[A-Z][A-Z0-9]{1,5}$`, a mnemonic of the rule family's domain.
- **`NNN`** — a 2–3 digit, zero-padded sequence, assigned in order within the home doc.
- A hyphen-segmented sub-series (`REG-DP-…`) is permitted; it resolves to its **leading prefix**
  (`REG`) for registration and single-source purposes.

## 2. Rules

1. **One prefix = one rule family, with one designated home file.** A prefix is globally unique.
   The invariant the model actually enforces is **every full ID has exactly one definition** (no
   duplicate `PFX-NNN`). A family normally lives entirely in its `home`; it MAY span additional
   docs *only* when the split is deliberate, the number space is coordinated across them, and no
   ID is defined twice — declared as `additional_homes` in the registry (e.g. `GRP` across
   resource-grouping + the Universal Group Model, which itself states "every GRP-* id has exactly
   one definition"). `additional_homes` is a sanctioned permanent arrangement; `baseline_spread`
   is temporary dedup **debt** to burn down. Both are checked; neither permits a duplicate ID.
2. **Definitions live only in the home.** A rule *definition* is a Markdown table row whose first
   cell is the ID (`| `PFX-NNN` | … |`). Those rows may appear **only** in the prefix's registered
   `home`. Everywhere else the ID is a **citation** (`see PFX-NNN`) — never a redefinition.
3. **Register before you mint.** A new prefix MUST be added to `rule-id-registry.yaml` before use.
   An unregistered prefix, or a definition outside its home, fails CI.
4. **IDs are immutable once published.** A live ID is never reused or repointed to a different
   rule — **retire and supersede** instead (the same immutability UDLM applies to versioned data).
   Retired numbers are not reused.
5. **Prefix collisions are resolved by renumbering to a disjoint prefix**, not by coexistence — the
   precedent is `REL-* → ERL-*`. The one-time pre-1.0 cleanup of the known collisions (ENT/GRP/INF/
   OBS) is tracked via `baseline_spread` in the registry and burned down before 1.0.

## 3. How enforcement works

`tests/check_single_source.py` reads the registry and, across the normative spec surface
(`tests/`, `.github/`, `docs/internal/` excluded), fails the build on:
- a **prefix defined in docs but not registered**;
- a **definition outside the prefix's `home`** (unless that file is grandfathered in the prefix's
  `baseline_spread`);
- the **same full ID defined in more than one file** (an id-collision — the sharpest form of the
  above).

A `baseline_spread` file that no longer contains a definition is reported as **stale** so it gets
removed — the check ratchets toward zero debt.

## 4. Adding a rule family

1. Pick a unique, mnemonic `PREFIX`.
2. Add an entry to `rule-id-registry.yaml` (`prefix`, `name`, `home`, `domain`, `status: active`).
3. Define the rules as ID-first table rows in the `home` doc; cite them by ID elsewhere.
4. `python3 tests/check_single_source.py` must pass.

# Authoring a bundle (and a custom profile)

**What this gets you.** One activatable unit — a bundle — that turns on (or off) the
capabilities, policies, settings, and mechanisms appropriate to a use and an environment.
**A profile is a bundle**: `udlm/profile/fsi` is a bundle whose contents are the governance
artifacts that posture requires. Authoring your own posture — "our regulated posture,"
"our lab posture" — is authoring a bundle, and nothing about the model changes when you do.

> **Read once, first:** [`README.md`](README.md) (the universal authoring contract),
> `registry/bundle.schema.json` (the record you are writing), and
> [`../spec/contracts/identifier-scheme.md`](../spec/contracts/identifier-scheme.md) §9 —
> every entry in a bundle is a URF reference.

## 1. When to use it — and when not

**Author a bundle** when a set of governed artifacts should be **switched on together** for a
deployment: a posture (profile), a module a subsystem needs, a baseline your org mandates
everywhere.

Do **not** author a bundle when:

- You are defining the artifact itself — a policy, a capability, a layer. A bundle
  **references, never defines**; the content lives in its own artifact and the bundle names it.
- You want a set of *resources* rather than a set of *governed artifacts* — that is an
  [`Access.Grouping`](../../registry/classes/access/grouping.yaml) (membership derived from a
  criterion), not a bundle.
- The value is a single setting with an obvious home — put it on the owning artifact's entry
  (`contains[].settings`) rather than minting a bundle for it.

## 2. The four things a bundle says

| Field | Says |
|---|---|
| `contains[]` | what this bundle turns on or off — one entry per governed artifact, `{ref, state}` |
| `composes[]` | which other bundles it contains (activation is transitive) |
| `settings` | bundle-level values with no artifact to reference |
| `activation` | properties of the *definition*: built-in, out-of-box default, approved |

**The state vocabulary is the whole floor model** (ADR-007 — a floor is a minimum, never a
filter):

- `required` — must be present and enforcing. This is the floor.
- `advisory` — enabled but non-blocking: it surfaces findings, it does not refuse.
- `off` — deliberately disabled in this posture. **Explicit and auditable**, and different
  from omission.
- **unlisted** — available but not mandated. Omission never means disabled; anyone can turn
  it on without changing the bundle.

That distinction is the one people get wrong: `homelab` does not *disable* the governance
matrix — it declines to mandate it (`advisory`), and a homelab operator who wants enforcement
raises it without forking anything. Reach for `off` only when the posture genuinely requires
the thing to be absent, and say why in `reason` (required for security-relevant artifacts).

## 3. Authoring a custom profile — the steps

1. **Start from the nearest built-in.** Six ship: `homelab`, `dev`, `standard`, `prod`, `fsi`,
   `sovereign` (`registry/instances/profile-*.yaml`; the characteristics are in
   [`../guides/profiles.md`](../guides/profiles.md)). Pick the one whose posture is closest —
   you will either compose it or copy it.
2. **Compose, don't copy, when you are adding.** If your posture is "`prod` plus our two
   mandates," declare `composes: ["estate/udlm/profile/prod"]` and list only your additions in
   `contains`. Composition is transitive and keeps you current when the built-in evolves.
   Copy only when your posture genuinely diverges.
3. **Write the entries.** Each is a URF reference plus a state:
   ```yaml
   contains:
     - ref: estate/policy/dual-approval-destructive
       state: required
     - ref: estate/discovery/scheduled
       state: advisory
       settings: {schedule: hourly}
     - ref: estate/audit/merkle-transparency
       state: off
       reason: no transparency-log operator in this environment; append-only audit still required
   ```
4. **Respect the composition rule.** A bundle **may not weaken** what a bundle it composes
   marks `required` — you cannot compose `fsi` and turn its attestation `off`. The validator
   refuses it (`registry/tools/validate.py` `check_bundle`). If you need a weaker posture,
   compose a lower built-in instead of weakening a higher one.
5. **Identity and versioning.** Mint a UUIDv4, take a handle in your own namespace
   (`acme/profile/regulated-eu` — never `udlm/…`, which is the substrate's), start at `1.0.0`,
   and version it like any artifact: a published (identity, version) pair is immutable, so any
   change ships a bump (`registry/VERSIONING.md`).
6. **Validate.** `python3 registry/tools/validate.py` — the bundle must validate against
   `bundle.schema.json` and pass `check_bundle` (URF-parseable refs, `off` reasons on
   security-relevant entries, no weakening on composition). `bash scripts/signoff.sh` runs
   everything CI will.

## 4. What activation means

A bundle record is **inert**. Activating it is a deployment act — *this deployment runs this
bundle* — and that state is recorded by the deployment, never inside the bundle. Two
consequences worth internalizing: the same bundle is byte-identical everywhere it is used
(which is what makes it a governed, shareable artifact), and "which posture are we running?"
is a question you ask the deployment, not the registry.

## 5. Completeness checklist — and the gate that enforces each

| Ships with it | Enforced by |
|---|---|
| Validates against `bundle.schema.json` | `registry/tools/validate.py` |
| Every `contains[].ref` / `composes[]` entry is a parseable URF reference | `check_bundle` + `tests/check_urf.py` |
| Every `off` on a security-relevant artifact carries a `reason` | `check_bundle` |
| No entry weakens a composed bundle's `required` | `check_bundle` |
| A published (identity, version) is never re-published with different bytes | `tests/check_identity_integrity.py` |

## 6. A worked pointer

Read `registry/instances/profile-homelab.yaml` — the built-in that exercises every state:
`required` floor entries, `advisory` operational entries with their settings, and one `off`
with its reason. `registry/instances/profile-fsi.yaml` shows a compliance posture where nearly
everything is `required`; `bundle.schema.json`'s inline `examples` entry is the minimal shape.

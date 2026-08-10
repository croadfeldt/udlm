# UDLM profile-settings index — every profile-governed knob and its one home

**Purpose.** One home per setting. This index lists every **profile-governed** setting (a value that varies across the `homelab | dev | standard | prod | fsi | sovereign` profiles) and the single doc/block that **owns** it. Before you write a per-profile value table, find the setting here and **reference its home** — do not restate the values. This is the settings companion to [`docs/file-index.md`](../docs/file-index.md) and the model in [ADR-015](../docs/adr/ADR-015-settings-and-config-bundles.md); the check `tests/check_single_source.py` flags a profile value table that appears for the same setting in more than one doc.

**The master overview** — the shape of profile scaling (which dimension tightens across profiles) — is the Profile Scaling Table in [`docs/spec/principles/design-priorities.md`](../docs/spec/principles/design-priorities.md). It is illustrative; the **authoritative per-profile values** live in each setting's owning bundle below.

**Where a profile-governed setting lives** (ADR-015 §2 — its `base`/`module`/`profile` tiers are one record kind now, the **profile**): the per-profile default set lives in its owning doc's config block, and a profile record selects among them by naming the artifact and its settings (`registry/profile.schema.json` `contains[].settings`).

| Setting | Bundle / owning block | What it governs per profile |
|---|---|---|
| `crypto.ca_algorithms` | `registry/standards-catalog.md` §3 | CA / mTLS certificate algorithm obligations per profile (P-384 preferred; P-256 where constrained; RSA floor) |
| `credential.max_lifetime` (per credential type) | `docs/spec/governance/credentials.md` §12.1 (`max_lifetime` block) | how long a credential is valid before rotation (e.g. `dcm_interaction`: homelab PT1H … sovereign PT15M) |
| `credential.rotation` / algorithm baseline / FIPS level / step-up MFA | `docs/spec/governance/credentials.md` §12.1 + §10 | rotation interval, forbidden-vs-approved algorithm set, FIPS floor, MFA requirement |
| `credential.callback_token_lifetime` | `docs/spec/contracts/provider-callback-auth.md` §5 | provider-callback token lifetime + pre-expiry rotation |
| `registry.version_policy` (default) | `docs/spec/governance/registry-governance.md` §4.3 | request-time version resolution default (`latest`/`compatible`/`exact`) |
| `registry.review_period` (by change type) | `docs/spec/governance/registry-governance.md` §3.2 | community review + shadow-validation durations |
| `registry.deprecation` / sunset window | `docs/spec/governance/registry-governance.md` §5 (`REG-DP-*`) | deprecation notice + tiered sunset periods |
| `authority.auto_approve_threshold` / approval tier | `docs/spec/governance/authority-tier-model.md` (vocabulary) + `docs/spec/principles/design-priorities.md` | how strict auto-approve is; which tier a decision needs |
| `contribution.shadow_mode` / auto-approve | `docs/spec/governance/federated-contribution-model.md` | shadow-mode duration before promotion; hub-contribution auto-approve |
| `zero_trust.posture` | `docs/spec/governance/accreditation-and-authorization-matrix.md` §5 | required zero-trust posture (`none`/…) + IP-binding |
| `observation.ttl` | `docs/spec/foundations/service-dependencies.md` (`OBS-005`) | observed-dependency staleness TTL |
| `time.sync_tolerance` | `docs/spec/contracts/time-and-clock.md` (per ADR-005) | clock-sync tolerance floor |
| `storage.failure_policy` | `docs/spec/contracts/storage-providers.md` §7 (`STO-002`) | store-failure behaviour (queue / abort / degrade) tightening for fsi/sovereign |
| `policy.min_lifecycle_scope` | `docs/spec/contracts/policy-contract.md` (profile minimums) | minimum lifecycle scope a compliance-class policy must cover (fsi/sovereign = `all`, cannot skip) |
| `policy.block_timeout` / override / escalation | `docs/spec/contracts/policy-contract.md` (timeout-behavior block) | block auto-cancel, override, and override-escalation timeouts (e.g. homelab PT48H … sovereign PT4H) |
| `provenance.default_level` | `docs/spec/foundations/layering-and-versioning.md` (profile defaults) | default provenance / implementation-posture detail (`full` … `hidden`) |
| `auth.available_modes` | `docs/spec/governance/auth-providers.md` §7–§8 | which authentication modes are available per profile + per-feature availability |
| `audit.granularity` / verification / overflow | `docs/spec/contracts/universal-audit.md` (`AUD-014/015/021`) | audit granularity (`stage`/`field`), inter-stage verification mode, commit-log overflow policy |

*Seeded 2026-07-15; grows as settings are added. When a new profile-governed setting is introduced, add its row here in the same change (SPEC-DESIGN §33). If a setting is not profile-governed, it does not belong here — it lives in its module doc without a per-profile table.*

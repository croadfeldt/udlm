# UDLM profile-settings index — every profile-governed knob and its one home

**Purpose.** One home per setting. This index lists every **profile-governed** setting (a value that varies across the `minimal | dev | standard | prod | fsi | sovereign` profiles) and the single doc/block that **owns** it. Before you write a per-profile value table, find the setting here and **reference its home** — do not restate the values. This is the settings companion to [`docs/file-index.md`](../docs/file-index.md) and the model in [ADR-015](../docs/adr/ADR-015-settings-and-config-bundles.md); the check `tests/check_single_source.py` flags a profile value table that appears for the same setting in more than one doc.

**The master overview** — the shape of profile scaling (which dimension tightens across profiles) — is the Profile Scaling Table in [`design-principles/design-priorities.md`](../design-principles/design-priorities.md). It is illustrative; the **authoritative per-profile values** live in each setting's owning bundle below.

**Bundle kinds** (ADR-015 §2): `base` (substrate default) · `module` (a subsystem's config block) · `profile` (the profile overlay). A profile-governed setting's per-profile default set lives in its owning **module** doc's config block; the profile bundle selects among them.

| Setting | Bundle / owning block | What it governs per profile |
|---|---|---|
| `credential.max_lifetime` (per credential type) | `governance/credentials.md` §12.1 (`max_lifetime` block) | how long a credential is valid before rotation (e.g. `dcm_interaction`: minimal PT1H … sovereign PT15M) |
| `credential.rotation` / algorithm baseline / FIPS level / step-up MFA | `governance/credentials.md` §12.1 + §10 | rotation interval, forbidden-vs-approved algorithm set, FIPS floor, MFA requirement |
| `credential.callback_token_lifetime` | `contracts/provider-callback-auth.md` §5 | provider-callback token lifetime + pre-expiry rotation |
| `registry.version_policy` (default) | `governance/registry-governance.md` §4.3 | request-time version resolution default (`latest`/`compatible`/`exact`) |
| `registry.review_period` (by change type) | `governance/registry-governance.md` §3.2 | community review + shadow-validation durations |
| `registry.deprecation` / sunset window | `governance/registry-governance.md` §5 (`REG-DP-*`) | deprecation notice + tiered sunset periods |
| `authority.auto_approve_threshold` / approval tier | `governance/authority-tier-model.md` (vocabulary) + `design-principles/design-priorities.md` | how strict auto-approve is; which tier a decision needs |
| `contribution.shadow_mode` / auto-approve | `governance/federated-contribution-model.md` | shadow-mode duration before promotion; hub-contribution auto-approve |
| `zero_trust.posture` | `governance/accreditation-and-authorization-matrix.md` §5 | required zero-trust posture (`none`/…) + IP-binding |
| `dependency.max_depth` | `entities/service-dependencies.md` (`DEP-015`) | max dependency-graph depth (e.g. 10 standard/prod, 7 fsi/sovereign) |
| `observation.ttl` | `entities/service-dependencies.md` (`OBS-005`) | observed-dependency staleness TTL |
| `time.sync_tolerance` | `contracts/time-and-clock.md` (per ADR-005) | clock-sync tolerance floor |
| `storage.failure_policy` | `contracts/storage-providers.md` §10 (`STO-002`) | store-failure behaviour (queue / abort / degrade) tightening for fsi/sovereign |

*Seeded 2026-07-15; grows as settings are added. When a new profile-governed setting is introduced, add its row here in the same change (SPEC-DESIGN §33). If a setting is not profile-governed, it does not belong here — it lives in its module doc without a per-profile table.*

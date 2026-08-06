# The six built-in profiles — personas, environments, and what actually differs

**A profile — a *deployment* profile — is one activatable unit**: its contents are the
governance artifacts that posture turns on, and engaging it is a deployment act (`registry/profile.schema.json`; the six
built-ins are `registry/profiles/*.yaml`). Authoring your own posture:
[`../authoring/profile.md`](../authoring/profile.md).

**What this settles (orientation, non-normative).** One page defining each built-in profile on five criteria —
**persona, target environment & estate lifetime, durability posture, failure semantics, approvals/automation** —
plus its expected use cases and the characteristics that actually differ between profiles. The authorities this
page defers to: **ADR-007** (what a profile *is*: a composed **set with a floor**, built-ins immutable,
fork-on-modify, platform-scoped), the per-profile ADRs (**017–022**, the *why* of each floor), the shipped
instances (`registry/profiles/*.yaml`, the floors themselves), and
[`registry/profile-settings-index.md`](../../registry/profile-settings-index.md) (one home per profile-governed
setting — **the** index for "what settings does a profile turn").

The ladder: **`homelab → dev → standard → prod → fsi → sovereign`**. (`minimal` is the retired pre-ADR-017 name
for `homelab` — naming charter.) Two facts frame everything: **a floor is a minimum, not a filter** (nothing
above the floor is disabled), and **every security property exists in every profile** (DPO-001) — profiles turn
strictness, thresholds, and automation, never existence.

---

## homelab — the single-operator on-ramp (ADR-017)

**Floor (the guaranteed minimum):** the `dev`-sized substrate — structural validation,
single-tenant ownership, resolved-profile evaluation, append-only audit, four-state tracking.
**Pre-tuned by `operational_config`, not mandated:** drift / recovery / discovery **on** at low
ceremony; governance-matrix **advisory**; approval ladder **none**; merkle-transparency audit
and attestation **off**. Nothing is disabled — a floor is a minimum, not a filter (ADR-007 §2);
making one of these floor-required is the custom-profile fork path.

| Criterion | |
|---|---|
| **Persona** | one operator running a real estate for themselves |
| **Target environment & lifetime** | home lab / small office; **long-lived** — a tiny prod (it's someone's actual DNS, storage, VMs) |
| **Durability posture** | keep-my-stuff: expiry/TTL off by default, drift detection on, backups matter, audit retention survives |
| **Failure semantics** | stability over experimentation — recoverability beats diagnostics verbosity |
| **Approvals/automation** | self-approval (one human); maximum automation; zero ceremony |

**Expected use cases:** personal infrastructure under real management; learning the system by living on it;
the adoption on-ramp that later grows into `standard`. **Not** for teams or anything customer-facing.

## dev — the evaluation & co-engineering target (ADR-018; the shipped default)

**Floor:** the smallest set that still runs the release use cases — structural validation,
single-tenant ownership, resolved-profile evaluation, append-only audit, four-state tracking,
the three stores, and causal-only time. No governance-matrix, attestation, or drift/recovery
mandate — those are exercised by the higher profiles; validating the UCs against `dev`
validates them for every profile (the ADR-007 invariant: identical architecture and wire
contracts, only the required floor differs).

| Criterion | |
|---|---|
| **Persona** | engineers building against or evaluating the system |
| **Target environment & lifetime** | shared eval/dev estates; **disposable** — built to be torn down and reset |
| **Durability posture** | aggressive TTL/auto-cleanup is a *feature*; short retention |
| **Failure semantics** | exercise the error paths: failure injection, verbose diagnostics, relaxed gates |
| **Approvals/automation** | none-to-team-level; iterate fast |

**Expected use cases:** running the 21-UC surface for evaluation; co-engineering; CI/test estates; demo
environments. The floor is deliberately the smallest that runs the whole architecture honestly.

**homelab vs dev in one line:** identical wire contracts, opposite *durability* orientation — homelab is a tiny
prod, dev is a scratchpad. That axis is why both exist.

## standard — baseline production (ADR-019)

**Floor:** `dev`'s **plus** the three things that separate "runs" from "operates" —
`policy/governance-matrix` (boundary enforcement on every DCM→Provider crossing),
`policy/recovery` (partial-implementation and timeout handling resolve deterministically), and
`policy/drift-reconciliation` + `discovery/scheduled` (drift detected and remediated on a
cadence). `standard ⊃ dev` — profiles compare by floor-containment (profile-resolution §2).

| Criterion | |
|---|---|
| **Persona** | a platform team running shared production for internal consumers |
| **Target environment & lifetime** | business production; long-lived, multi-tenant |
| **Durability posture** | full enforcement; versioned everything; real retention |
| **Failure semantics** | recovery policies active; drift remediated, not just detected |
| **Approvals/automation** | team approvals on privileged operations; automation with guardrails |

**Expected use cases:** the default choice for real workloads without a regulatory driver.

## prod — hardened production (ADR-020)

**Floor:** `standard`'s **plus** blast-radius-aware change control and bounded execution —
`policy/blast-radius-impact` (changes gated against what they actually reach),
`policy/dual-approval-destructive` (a human gate on irreversible actions), and
`recovery/bounded-convergence` + tighter dispatch timeouts (retries bounded with a
terminal-failure surface, so convergence cannot loop indefinitely). `prod ⊃ standard ⊃ dev`.

| Criterion | |
|---|---|
| **Persona** | operations owning availability commitments |
| **Target environment & lifetime** | hardened, SLA-bearing production |
| **Durability posture** | standard's, hardened — shorter credential lifetimes, stricter thresholds, geo-redundancy posture |
| **Failure semantics** | fail-safe defaults; escalation ladders wired |
| **Approvals/automation** | stricter approval routing; change windows |

**Expected use cases:** production with uptime/cost governance obligations but no sector regulator.

## fsi — regulated financial services (ADR-021)

**Floor:** `prod`'s **plus** the compliance dimension — tamper-evident Merkle-transparency
audit with inclusion/consistency proofs (universal-audit §8, RFC 9162); attestation-gated,
**verifiable** provider admission (the accreditation's proof chains to a trust anchor and is
verified before scope is appraised — the two-gate, matrix §3.7/§3.8); governance-matrix on
**every** lifecycle operation; the time-bounded override-approval workflow; attested time; and
regulatory retention. A distinct *kind* of set (a compliance posture), not merely `prod`+more.

| Criterion | |
|---|---|
| **Persona** | platform + compliance in a regulated financial institution |
| **Target environment & lifetime** | audited production under sector regulation |
| **Durability posture** | field-level audit, long retention, tamper-evident everything |
| **Failure semantics** | deny-by-default at boundaries; human escalation on governance conflicts |
| **Approvals/automation** | dual-control on privileged actions; hardware MFA; attestation-gated integrations |

**Expected use cases:** FSI estates where the regulator reads the audit trail.

## sovereign — data sovereignty, the strictest floor (ADR-022)

**Floor:** `fsi`'s **plus** the sovereignty dimension — in-boundary key material (audit
signing keys never leave the boundary, AUD-012); sovereign-only placement with the sovereignty
declaration **attested**, never self-asserted; data-plane-attested residency (conveyed to and
attested by the enforcing provider — `enforcement_plane`, matrix §3.8); and sub-processor
restriction (no unauthorized downstream access). Spatial confinement is its own dimension; a
stricter need forks `sovereign` as a custom profile.

| Criterion | |
|---|---|
| **Persona** | operators of jurisdiction-bound / government estates |
| **Target environment & lifetime** | sovereign or air-gapped deployments; residency-bound |
| **Durability posture** | in-jurisdiction everything; signed-bundle export; longest retention |
| **Failure semantics** | hard DENY on residency/classification conflicts; `PENDING_REVIEW` over silent proceed |
| **Approvals/automation** | accreditation + hardware attestation gates; no federation to lower-posture peers |

**Expected use cases:** sovereign cloud, classified-adjacent estates, jurisdiction-pinned data.

---

## What actually differs — the characteristics matrix

Each row names the axis and its **owning table** (values live there, once — cite, don't restate):

| Axis | Owner |
|---|---|
| Every profile-governed **setting** (the full list) | [`registry/profile-settings-index.md`](../../registry/profile-settings-index.md) |
| Security-property strictness (existence never varies) | `docs/spec/principles/design-priorities.md` §security table (DPO-001) |
| Audit **granularity** (stage → mutation → field) + retention | `docs/spec/contracts/universal-audit.md` §8.1 |
| Zero-trust **posture** default (`none → boundary → full → hardware_attested`) | `docs/spec/governance/accreditation-and-authorization-matrix.md` §zero-trust ladder |
| Credential lifetimes / rotation / binding | `docs/spec/contracts/provider-callback-auth.md` §ladder + `docs/spec/governance/credentials.md` |
| Provenance **carrier** (derivable at homelab → full-inline where mandated) | `docs/spec/foundations/data-model-core.md` E4 / `layering-and-versioning.md` §provenance groups |
| Store bindings (git as conforming carrier at homelab → per-tenant/WORM at fsi/sovereign) | `docs/spec/foundations/four-states.md` §store note ([D1]) |
| Tenancy enforcement (`advisory` at homelab → hard boundaries) | `docs/spec/foundations/universal-groups.md` §enforcement model |
| Trust/attestation floors per plane (implementation defaults) | DCM `architecture/trust-profiles.md` (implementation-side) |

**The durability axis** (the one this page adds, per the profile ADRs' intent): homelab and dev sit at the same
*strictness* end of the ladder but opposite *durability* ends — a distinction the settings tables don't carry
because it lives in defaults orientation (TTL/expiry, retention, cleanup automation), not floors.

---

*Every profile is immutable as shipped; modifying one forks a custom profile under your own name (ADR-007).
Selection guidance in one line: solo and real → homelab; team and disposable → dev; production → standard;
SLA-bearing → prod; regulated → fsi; jurisdiction-bound → sovereign.*

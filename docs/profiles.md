# The six built-in profiles — personas, environments, and what actually differs

**What this settles (orientation, non-normative).** One page defining each built-in profile on five criteria —
**persona, target environment & estate lifetime, durability posture, failure semantics, approvals/automation** —
plus its expected use cases and the characteristics that actually differ between profiles. The authorities this
page defers to: **ADR-007** (what a profile *is*: a composed **set with a floor**, built-ins immutable,
fork-on-modify, platform-scoped), the per-profile ADRs (**017–022**, the *why* of each floor), the shipped
instances (`registry/instances/profile-*.yaml`, the floors themselves), and
[`registry/profile-settings-index.md`](../registry/profile-settings-index.md) (one home per profile-governed
setting — **the** index for "what settings does a profile turn").

The ladder: **`homelab → dev → standard → prod → fsi → sovereign`**. (`minimal` is the retired pre-ADR-017 name
for `homelab` — naming charter.) Two facts frame everything: **a floor is a minimum, not a filter** (nothing
above the floor is disabled), and **every security property exists in every profile** (DPO-001) — profiles turn
strictness, thresholds, and automation, never existence.

---

## homelab — the single-operator on-ramp (ADR-017)

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

| Criterion | |
|---|---|
| **Persona** | a platform team running shared production for internal consumers |
| **Target environment & lifetime** | business production; long-lived, multi-tenant |
| **Durability posture** | full enforcement; versioned everything; real retention |
| **Failure semantics** | recovery policies active; drift remediated, not just detected |
| **Approvals/automation** | team approvals on privileged operations; automation with guardrails |

**Expected use cases:** the default choice for real workloads without a regulatory driver.

## prod — hardened production (ADR-020)

| Criterion | |
|---|---|
| **Persona** | operations owning availability commitments |
| **Target environment & lifetime** | hardened, SLA-bearing production |
| **Durability posture** | standard's, hardened — shorter credential lifetimes, stricter thresholds, geo-redundancy posture |
| **Failure semantics** | fail-safe defaults; escalation ladders wired |
| **Approvals/automation** | stricter approval routing; change windows |

**Expected use cases:** production with uptime/cost governance obligations but no sector regulator.

## fsi — regulated financial services (ADR-021)

| Criterion | |
|---|---|
| **Persona** | platform + compliance in a regulated financial institution |
| **Target environment & lifetime** | audited production under sector regulation |
| **Durability posture** | field-level audit, long retention, tamper-evident everything |
| **Failure semantics** | deny-by-default at boundaries; human escalation on governance conflicts |
| **Approvals/automation** | dual-control on privileged actions; hardware MFA; attestation-gated integrations |

**Expected use cases:** FSI estates where the regulator reads the audit trail.

## sovereign — data sovereignty, the strictest floor (ADR-022)

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
| Every profile-governed **setting** (the full list) | [`registry/profile-settings-index.md`](../registry/profile-settings-index.md) |
| Security-property strictness (existence never varies) | `design-principles/design-priorities.md` §security table (DPO-001) |
| Audit **granularity** (stage → mutation → field) + retention | `observability/universal-audit.md` §8.1 |
| Zero-trust **posture** default (`none → boundary → full → hardware_attested`) | `governance/accreditation-and-authorization-matrix.md` §zero-trust ladder |
| Credential lifetimes / rotation / binding | `contracts/provider-callback-auth.md` §ladder + `governance/credentials.md` |
| Provenance **carrier** (derivable at homelab → full-inline where mandated) | `foundations/data-model-core.md` E4 / `layering-and-versioning.md` §provenance groups |
| Store bindings (git as conforming carrier at homelab → per-tenant/WORM at fsi/sovereign) | `foundations/four-states.md` §store note ([D1]) |
| Tenancy enforcement (`advisory` at homelab → hard boundaries) | `observability/universal-groups.md` §enforcement model |
| Trust/attestation floors per plane (realization defaults) | DCM `architecture/trust-profiles.md` (realization-side) |

**The durability axis** (the one this page adds, per the profile ADRs' intent): homelab and dev sit at the same
*strictness* end of the ladder but opposite *durability* ends — a distinction the settings tables don't carry
because it lives in defaults orientation (TTL/expiry, retention, cleanup automation), not floors.

---

*Every profile is immutable as shipped; modifying one forks a custom profile under your own name (ADR-007).
Selection guidance in one line: solo and real → homelab; team and disposable → dev; production → standard;
SLA-bearing → prod; regulated → fsi; jurisdiction-bound → sovereign.*

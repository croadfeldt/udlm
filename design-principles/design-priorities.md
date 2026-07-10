# UDLM — Design Principles

**Document Status:** ✅ Stable — UDLM substrate contract
**Document Type:** Substrate Reference — Design Philosophy
**Related Documents:** [Foundational Abstractions](../foundations/foundations.md) | [Authority Tier Model](../governance/authority-tier-model.md) | [Provider Contract](../contracts/provider-contract.md) | [Policy Contract](../contracts/policy-contract.md)

> **This document maps to: DATA + PROVIDER + POLICY**
>
> Design priorities govern every decision across all three abstractions. They are not guidelines — they are the decision framework used when priorities conflict. Every contributor, implementer, and reviewer of a UDLM realization should apply this framework.

---

## Design Principles as Interoperability Substrate

The four principles below are **invariant**. Any realization conformant to UDLM must honor them; they are the contract foundation. Specific enforcement strictness, threshold values, and operational trade-offs are realization choices (a peer implementation could pick differently and still be a valid UDLM peer). The principles themselves are not negotiable.

When priorities conflict, higher priorities win. When there is no conflict, all four apply simultaneously.

---

### Priority 1 — Industry Best Practices for Security

Security is not a feature, a profile option, or a compliance checkbox. It is the baseline that every other design decision must respect.

**What this means:**

Security properties — value separation, rotation, audit trails, idle detection, algorithm baselines, scoped credentials, revocation propagation, shadow mode evaluation — are **architecturally present in every profile**. What profiles control is enforcement strictness, threshold values, and automation level — not whether the security property applies.

**The `minimal` profile is "security with minimal operational overhead" — not "minimal security."**

A `minimal` profile realization:
- Rotates credentials (at longer intervals with manual triggers acceptable — not never)
- Detects idle credentials (at a generous threshold — not never)
- Requires algorithm baselines (via forbidden list — not null)
- Runs shadow mode on contributed policies (always — not optionally)
- Audits first credential retrieval (always — not sometimes)
- Maintains revocation registry (with bounded cache TTL — not disabled)

The security model is present and correct. The enforcement strictness and automation burden are reduced.

**When security and convenience conflict, security wins** — but the design must find a way to make the secure option easy. A security model that is routinely bypassed because it is too burdensome has failed at both security and usability. The profile system is the mechanism: the right profile makes secure behavior automatic, not effortful.

**Security properties that are non-negotiable in all profiles:**

| Property | Rule | Reference |
|----------|------|-----------|
| Credential values never in realization-internal stores of consumer-facing credentials | Absolute, no profile exception | [credentials](../governance/credentials.md) |
| Governance Matrix always boolean | Scoring never applies to boundary decisions | [governance-matrix](../governance/governance-matrix.md) |
| Every provider dispatch requires scoped interaction credential | Substrate requirement | [credentials](../governance/credentials.md) |
| Shadow mode on all contributed policies | Substrate requirement | [federated-contribution-model](../governance/federated-contribution-model.md) |
| Bounded auto-approve threshold in all profiles | Substrate requirement | [authority-tier-model](../governance/authority-tier-model.md) |
| First credential retrieval always audited | Substrate requirement | [credentials](../governance/credentials.md) |
| Forbidden algorithm baseline always enforced | Substrate requirement (no null approved_algorithms) | [credentials](../governance/credentials.md) |
| Revocation registry always maintained | Substrate requirement | [credentials](../governance/credentials.md) |

---

### Priority 2 — Ease of Use

A UDLM realization exists to enable self-service for consumers. If the right path is also the hard path, consumers will find other paths — and those other paths are ungoverned.

**What this means:**

The secure path must also be the easy path. Profile defaults should work for most deployments without customization. Ordinary requests should auto-approve without human intervention. Policy authoring should not require deep policy-language expertise for common patterns. Consumer-facing surfaces (GUIs, scoring models, contribution endpoints) exist to make governed behavior less operationally burdensome.

**Ease of use serves security.** An organization that finds the system too cumbersome and routes requests outside it has eliminated all of its security benefits. A team that circumvents credential management because it's too complex has no credential management.

**The design principle:** When implementing a security requirement, simultaneously design the ease-of-use mechanism that makes it effortless to comply with. A scoring model's auto-approval threshold (not making every request require human review) is ease of use in service of security.

**Things that should be easy in all profiles:**
- Requesting a standard resource (auto-approve for clean requests)
- Authoring a common policy without specialized expertise
- Retrieving a credential after resource provisioning (direct API call)
- Understanding why a request was scored a certain way
- Contributing a policy through an API rather than a manual workflow

---

### Priority 3 — Extensibility and Capability Grouping

The profile system, compliance domain overlays, policy groups, capability extensions, and registry governance make UDLM adaptable to arbitrary organizational requirements without code changes.

**What this means:**

New compliance requirements should be expressible as policy additions within the existing framework. New provider types should fit the existing Provider base contract. New deployment contexts should be addressable through profile configuration. A substrate that requires modifying source code for each new deployment context is not a substrate — it is a template.

**Grouping is the mechanism for extensibility.** Compliance domain overlays compose with base profiles. Policy groups compose with profile policies. Capability extensions compose with base provider contracts. The three-abstraction model (Data, Provider, Policy) is the foundation that makes all of this compositional.

**Extensibility must not compromise security or usability.** An extension mechanism that allows downstream users to disable security properties (rather than scale them) fails priority 1. An extension mechanism that requires expertise to configure fails priority 2. Hard constraints (bounded auto-approve, value-separation for credentials) are precisely the boundaries that prevent extensibility from undermining security.

---

### Priority 4 — Fit for Purpose (Always Required)

A UDLM realization must manage data center infrastructure lifecycle. All of the above is in service of this purpose. An architecturally beautiful system that cannot provision a VM, track its drift, and decommission it cleanly has failed at its reason for existing.

**What this means:**

Design decisions that serve priorities 1–3 but break the end-to-end lifecycle (request → provision → operate → decommission) are not acceptable. Every capability added must have a clear answer to "how does this serve the lifecycle management mission?"

Fit for purpose is not a fourth priority that can be traded against the first three — it is a precondition. If a design cannot fulfill its stated purpose, priorities 1–3 become irrelevant. This is why it is listed fourth rather than first: it is assumed, not aspirational.

---

## Applying the Priorities — Decision Framework

The sequence below is **descriptive design rationale** — it records how the priority order resolves a conflict, so a reader can reconstruct *why* a decision went the way it did. It is not a runbook and not enforced by tooling: the concrete, testable thresholds a realization must meet live in [CONFORMANCE](../CONFORMANCE.md), and this document stays at the level of *principle*. Read the steps as "the priority order implies…", not as commands.

When priorities seem to conflict, the resolution follows this order:

```
1. Does this design decision compromise a non-negotiable security property?
   YES → redesign until it does not. No exceptions.

2. Does the secure option create significant operational burden?
   YES → design the ease-of-use mechanism simultaneously.
         The secure path must also be the easy path.
         If you cannot make it easy enough, reconsider whether the
         security property is correctly scoped.

3. Can this behavior be expressed through the existing profile/policy/extension system?
   YES → use it. Do not add new mechanisms when existing ones suffice.
   NO  → extend the existing mechanism before creating a new one.

4. Does this design decision support the complete lifecycle?
   NO  → do not proceed until it does.
```

### Common Misapplications

**"We can disable X in the minimal profile for simplicity."**
Wrong application. The minimal profile scales down operational burden, not security properties. The question is: what is the minimum viable implementation of X that requires no operational overhead? That is what minimal profile gets.

**"Security is too complex for our users, so we'll make it optional."**
Wrong application. If security is too complex, the design of the security mechanism needs to improve (priority 2). Making security optional removes it — that fails priority 1. Design a simpler mechanism that achieves the same security outcome.

**"We need a new mechanism for this capability."**
Wrong starting point (priority 3 failure). The question is: can this be expressed through profiles, policies, provider capability extensions, or compliance overlays? Usually yes. If genuinely not, extend the nearest existing mechanism rather than creating a new one.

**"This edge case isn't part of the lifecycle."**
Wrong framing (priority 4). Every edge case in the lifecycle — partial realization, compensation, drift remediation, credential revocation on decommission — is part of the lifecycle. Fit for purpose means handling the complete lifecycle, not just the happy path.

---

## Profile Scaling Model (Definition)

The profile system is the primary mechanism for expressing priorities 1–3 simultaneously. Understanding what profiles control — and what they do not — is essential to applying the priority order correctly.

**Profiles control:**
- Enforcement strictness (how strictly a security property is enforced)
- Threshold values (how long, how often, how many)
- Automation level (automated vs manual trigger)
- Approval tier (auto-approve vs human review vs verified vs authorized)
- Review periods (how long shadow mode runs before promotion)

**Profiles do not control:**
- Whether a security property is present (it always is)
- Which non-negotiable constraints apply
- Whether the audit trail is maintained (always maintained; retention varies)
- Whether the data model is valid (schema conformance is not profile-dependent)

### Named Profiles (Substrate Vocabulary)

UDLM defines the following named profiles as the substrate vocabulary. Realizations may extend with additional named profiles but must support the substrate set so that artifacts and contributions referencing these names interoperate across peers.

- `minimal` — security with minimal operational overhead
- `dev` — developer/lab settings with relaxed thresholds
- `standard` — typical production-ish defaults
- `prod` — strict production
- `fsi` — financial-services-industry compliance overlay
- `sovereign` — sovereignty/regulated-jurisdiction overlay

### Profile Scaling Table (Reference)

The table below illustrates the **shape** of profile scaling. Specific threshold values are realization-defined (a peer realization MAY pick different absolute values). What is invariant is the monotonic ordering: stricter profiles must be at least as strict as looser profiles on every dimension. "Present" means the property is architecturally required — what varies is the configuration.

| Security Property | minimal | dev | standard | prod | fsi | sovereign |
|------------------|---------|-----|----------|------|-----|-----------|
| Credential rotation | Required; longer interval; manual OK | Required; medium interval; manual OK | Required; automated | Required; strict interval | Required; short interval | Required; hardware-triggered |
| Idle detection threshold | Loose | Medium | Tight | Tighter | Very tight | Hourly-class |
| Algorithm baseline | Forbidden list | Forbidden list | Approved list | Approved list | FIPS-only | HSM-generated only |
| Shadow mode on contribution | Always on | Always on | Always on | Always on | Always on | Always on |
| First retrieval audit | Always | Always | Always | Always | Always | Always |
| Revocation cache TTL | Loose | Loose | Tight | Tight | Tighter | Tightest |
| Auto-approve threshold | Looser | Loose | Moderate | Strict | Stricter | Strictest |
| Step-up MFA for credentials | Optional | Optional | Sensitive types | All types | Hardware MFA | mTLS |
| FIPS level | None required | None required | None required | Level 1 | Level 2 | Level 3 |
| IP binding | Not required | Not required | Not required | Not required | Required | Required |
| Hub contribution auto-approve | Yes | Yes | Yes | No (human review) | No (verified) | No (authorized) |

---

## Authority Tiers (Model Definition)

UDLM defines an ordered authority tier vocabulary that applies to requests, policy contributions, provider registrations, and any pipeline decision requiring human authorization. The tier vocabulary is the substrate; the runtime enforcement mechanisms are realization choices.

> **Full specification:** See [Authority Tier Model](../governance/authority-tier-model.md) for the complete ordered tier list, custom tier contribution model, dynamic threshold format, and tier-governing system policies.

### Default Tier Vocabulary

| Tier | Required authority level | Substrate role |
|------|-------------------------|-----------------|
| `auto` | None — `decision_gravity: none`; system confidence sufficient | Validation passes; automatic activation |
| `reviewed` | Standard authority — `decision_gravity: routine`; one qualified reviewer in the relevant domain | One actor with reviewer role records a decision |
| `verified` | Elevated authority — `decision_gravity: elevated`; independent confirmation required; separation of duties | Two distinct actors with reviewer role each record a decision |
| `authorized` | Senior/governing authority — `decision_gravity: critical`; highest organizational weight; most consequential decisions | N members of the declared group record decisions within a window |

### Tier Extensibility Contract

The four default tiers (`auto`, `reviewed`, `verified`, `authorized`) are UDLM substrate defaults. Realizations and organizations may add custom tiers by inserting them into the ordered list between existing tiers. The tier name is stable; numeric weight is derived from list position at evaluation time. This extensibility is part of the substrate contract — any conformant realization must accept custom tier insertions and evaluate them consistently.

Example: An organization adds `compliance_reviewed` between `verified` and `authorized`:
```
auto → reviewed → verified → compliance_reviewed → authorized
```
All existing references to `authorized` continue to work. Only the threshold ranges in the affected profile need updating. See [Authority Tier Model](../governance/authority-tier-model.md).

### The `authorized` Tier — Substrate Definition

UDLM defines `authorized` as the tier requiring quorum decision-making by a declared group. The substrate requires:

1. **Group membership** — which actors constitute the authorized group
2. **Quorum declaration** — `N of M` threshold declared in the profile or per-decision configuration
3. **Notification routing** — when a decision enters `pending_authorized` state, notifications fire to all group members
4. **Vote recording surface** — an API or equivalent surface by which members (or external systems acting on their behalf) record `approve` or `reject`
5. **Quorum tracking** — votes are counted and the pipeline advances when N is reached
6. **Audit trail** — every vote is audited with actor identifier, timestamp, decision, and the system that recorded it

UDLM does not specify how the organization deliberates or which external systems integrate with the vote recording surface. The substrate requires only that decisions are recorded against an authenticated authorized-group member.

### Deadline and Escalation (Substrate Vocabulary)

UDLM defines the vocabulary for approval windows and on-expiry policies. Specific window durations are realization-configurable:

```yaml
approval_window:
  reviewed: <duration>
  verified: <duration>
  authorized: <duration>
  on_expiry:
    reviewed:  escalate | reject
    verified:  escalate | reject
    authorized:    escalate | reject
```

The `on_expiry` action vocabulary (`escalate`, `reject`) is closed at the substrate. Realizations MUST implement both; window durations MAY vary per realization and per profile.

---

## System Policies (Substrate)

| Policy | Rule |
|--------|------|
| `DPO-001` | Security properties are architecturally present in all profiles. Profiles control enforcement strictness, thresholds, and automation level — not whether the property exists. |
| `DPO-002` | Every security requirement must be accompanied by an ease-of-use mechanism that makes compliance effortless for the common case. A security model routinely bypassed because of complexity has failed. |
| `DPO-003` | New capabilities should be expressed through the existing profile/policy/provider extension system before creating new mechanisms. Extensibility is achieved through composition, not proliferation. |
| `DPO-004` | Fit for purpose is a precondition, not a priority. All four priorities apply only within the constraint that the system can fulfill its lifecycle management mission. |
| `DPO-005` | The `minimal` profile is "security with minimal operational overhead" — not "minimal security." Design decisions that disable security properties rather than scaling them violate DPO-001. |
| `DPO-006` | When security and ease of use conflict, redesign the ease-of-use mechanism — not the security requirement. The secure path must also be the easy path. |

---

*UDLM substrate document. Realization implementation details (specific thresholds, enforcement code, profile-governed runtime constraints, policy-as-code engine integration, documentation discipline) live in the consuming realization's repository.*

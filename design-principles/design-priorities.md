# DCM Design Priorities

**Document Status:** ✅ Stable — Foundational reference
**Document Type:** Architecture Reference — Design Philosophy
**Related Documents:** [Foundational Abstractions](00-foundations.md) | [Policy Profiles](14-policy-profiles.md) | [Scoring Model](29-scoring-model.md) | [credential management service Model](31-credential-provider-model.md)

> **This document maps to: DATA + PROVIDER + POLICY**
>
> Design priorities govern every decision across all three abstractions. They are not guidelines — they are the decision framework used when priorities conflict. Every contributor, implementer, and reviewer should apply this framework.
> See also: [Provider Contract](A-provider-contract.md) | [Policy Contract](B-policy-contract.md)

---

## The Four Priorities

Every design decision in DCM is evaluated against this hierarchy. When priorities conflict, higher priorities win. When there is no conflict, all four apply simultaneously.

---

### Priority 1 — Industry Best Practices for Security

Security is not a feature, a profile option, or a compliance checkbox. It is the baseline that every other design decision must respect.

**What this means:**

Security properties — value separation, rotation, audit trails, idle detection, algorithm baselines, scoped credentials, revocation propagation, shadow mode evaluation — are **architecturally present in every profile**. What profiles control is enforcement strictness, threshold values, and automation level — not whether the security property applies.

**The `minimal` profile is "security with minimal operational overhead" — not "minimal security."**

A `minimal` profile deployment:
- Rotates credentials (at longer intervals with manual triggers acceptable — not never)
- Detects idle credentials (at a generous P30D threshold — not never)
- Requires algorithm baselines (via forbidden list — not null)
- Runs shadow mode on contributed policies (always — not optionally)
- Audits first credential retrieval (always — not sometimes)
- Maintains revocation registry (at PT5M cache TTL — not disabled)

The security model is present and correct. The enforcement strictness and automation burden are reduced.

**When security and convenience conflict, security wins** — but the design must find a way to make the secure option easy. A security model that is routinely bypassed because it is too burdensome has failed at both security and usability. The profile system is the mechanism: the right profile makes secure behavior automatic, not effortful.

**Security properties that are non-negotiable in all profiles:**

| Property | Rule | Reference |
|----------|------|-----------|
| Credential values never in DCM stores | CPX-001 — absolute, no profile exception | doc 31 |
| Governance Matrix always boolean | SMX-004 — scoring never applies to boundary decisions | doc 29 |
| Every provider dispatch requires scoped interaction credential | CPX-002 | doc 31 |
| Shadow mode on all contributed policies | FCM-004 | doc 28 |
| auto_approve_below ≤ 50 in all profiles | SMX-008 | doc 29 |
| First credential retrieval always audited | CPX-005 | doc 31 |
| Forbidden algorithm baseline always enforced | CPX-009 (no null approved_algorithms) | doc 31 |
| Revocation registry always maintained | CPX-003 | doc 31 |

---

### Priority 2 — Ease of Use

DCM exists to enable self-service for application teams. If the right path is also the hard path, teams will find other paths — and those other paths are ungoverned.

**What this means:**

The secure path must also be the easy path. Profile defaults should work for most deployments without customization. Ordinary requests should auto-approve without human intervention. Policy authoring should not require Rego expertise for common patterns. The Flow GUI, scoring model, and consumer contribution endpoints all exist to make governed behavior less operationally burdensome.

**Ease of use serves security.** An organization that finds DCM too cumbersome and routes requests outside DCM has eliminated all of DCM's security benefits. A homelab team that circumvents credential management because it's too complex has no credential management.

**The design principle:** When implementing a security requirement, simultaneously design the ease-of-use mechanism that makes it effortless to comply with. The scoring model's auto-approval threshold (not making every request require human review) is ease of use in service of security.

**Things that should be easy in all profiles:**
- Requesting a standard resource (auto-approve for clean requests)
- Authoring a common policy without Rego expertise (visual condition builder)
- Retrieving a credential after resource provisioning (direct API call)
- Understanding why a request was scored a certain way (score_drivers field)
- Contributing a policy (API endpoint, not manual GitOps PR)

---

### Priority 3 — Extensibility and Capability Grouping

The profile system, compliance domain overlays, policy groups, capability extensions, and registry governance make DCM adaptable to arbitrary organizational requirements without code changes.

**What this means:**

New compliance requirements should be expressible as policy additions within the existing framework. New provider types should fit the existing Provider base contract. New deployment contexts should be addressable through profile configuration. A platform that requires modifying source code for each new deployment context is not a platform — it is a template.

**Grouping is the mechanism for extensibility.** Compliance domain overlays compose with base profiles. Policy groups compose with profile policies. Capability extensions compose with base provider contracts. The three-abstraction model (Data, Provider, Policy) is the foundation that makes all of this compositional.

**Extensibility must not compromise security or usability.** An extension mechanism that allows downstream users to disable security properties (rather than scale them) fails priority 1. An extension mechanism that requires expertise to configure fails priority 2. The profile system's hard constraints (SMX-008: auto_approve ≤ 50; CPX-001: no values in DCM stores) are precisely the boundaries that prevent extensibility from undermining security.

---

### Priority 4 — Fit for Purpose (Always Required)

DCM must manage data center infrastructure lifecycle. All of the above is in service of this purpose. An architecturally beautiful system that cannot provision a VM, track its drift, and decommission it cleanly has failed at its reason for existing.

**What this means:**

Design decisions that serve priorities 1–3 but break the end-to-end lifecycle (request → provision → operate → decommission) are not acceptable. Every capability added must have a clear answer to "how does this serve the lifecycle management mission?"

Fit for purpose is not a fourth priority that can be traded against the first three — it is a precondition. If a design cannot fulfill its stated purpose, priorities 1–3 become irrelevant. This is why it is listed fourth rather than first: it is assumed, not aspirational.

---

## Applying the Priorities — Decision Framework

When facing a design decision where priorities seem to conflict, apply this sequence:

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

## Profile Scaling Model

The profile system is the primary mechanism for expressing priorities 1–3 simultaneously. Understanding what profiles control — and what they do not — is essential to applying the priority order correctly.

**Profiles control:**
- Enforcement strictness (how strictly a security property is enforced)
- Threshold values (how long, how often, how many)
- Automation level (automated vs manual trigger)
- Approval tier (auto-approve vs human review vs verified vs authorized)
- Review periods (how long shadow mode runs before promotion)

**Profiles do not control:**
- Whether a security property is present (it always is)
- Which non-negotiable constraints apply (CPX-001, SMX-004, SMX-008, etc.)
- Whether the audit trail is maintained (always maintained; retention varies)
- Whether the data model is valid (schema conformance is not profile-dependent)

### Profile Scaling Table

This table shows how representative security properties scale across profiles. "Present" means the property is architecturally required — what varies is the configuration.

| Security Property | minimal | dev | standard | prod | fsi | sovereign |
|------------------|---------|-----|----------|------|-----|-----------|
| Credential rotation | Required; P365D max; manual OK | Required; P180D max; manual OK | Required; automated | Required; strict interval | Required; P90D max | Required; hardware-triggered |
| Idle detection threshold | P30D | P14D | P7D | P3D | P1D | PT12H |
| Algorithm baseline | Forbidden list | Forbidden list | Approved list | Approved list | FIPS-only | HSM-generated only |
| Shadow mode on contribution | Always on | Always on | Always on | Always on | Always on | Always on |
| First retrieval audit | Always | Always | Always | Always | Always | Always |
| Revocation cache TTL | PT5M | PT5M | PT1M | PT1M | PT30S | PT15S |
| Auto-approve threshold | ≤ 45 | ≤ 40 | ≤ 25 | ≤ 15 | ≤ 10 | ≤ 5 |
| Step-up MFA for credentials | Optional | Optional | Sensitive types | All types | Hardware MFA | mTLS |
| FIPS level | None required | None required | None required | Level 1 | Level 2 | Level 3 |
| IP binding | Not required | Not required | Not required | Not required | Required | Required |
| Hub contribution auto-approve | Yes | Yes | Yes | No (human review) | No (verified) | No (authorized) |

---

---

## Approval Tier Model

DCM defines four approval tiers that apply to requests, policy contributions, provider registrations, and any pipeline decision requiring human authorization. Understanding the model is critical: **DCM provides the gate and the audit trail. The review process is the organization's responsibility.**

> **Full specification:** See [Authority Tier Model](32-authority-tier-model.md) for the complete ordered tier list, custom tier contribution model, dynamic threshold format, and ATM-001–ATM-008 system policies.

### What DCM Does vs What Organizations Provide

| Tier | Required authority level | DCM provides | Organization provides | DCM gate condition |
|------|-------------------------|-------------|----------------------|-------------------|
| `auto` | None — `decision_gravity: none`; system confidence sufficient | Structural and governance validation; automatic activation on pass | Nothing — fully automated | All validation checks pass |
| `reviewed` | Standard authority — `decision_gravity: routine`; one qualified reviewer in the relevant domain | Approval record; eligible reviewer notification via notification service; pipeline hold; decision recording via Admin API; activation or rejection | Who constitutes a qualified reviewer; the review process; recording the decision via DCM API or an external system that calls it | One actor with reviewer role records a decision via the Admin API |
| `verified` | Elevated authority — `decision_gravity: elevated`; independent confirmation required; separation of duties | Approval record requiring two independent decisions; enforces distinct actors (same actor cannot provide both); eligible reviewer notification; pipeline hold | Who constitutes qualified reviewers; both review processes; may use external workflow tools that call the DCM API | Two distinct actors with reviewer role each record a decision via the Admin API |
| `authorized` | Senior/governing authority — `decision_gravity: critical`; highest organizational weight; most consequential decisions | Approval record specifying the required DCMGroup and threshold (N of M); group member notification; pipeline hold; individual decision tracking via Admin API; threshold evaluation; activation when N reached | Who constitutes the authority group (one person with delegated authority, a CTO, a CISO and legal counsel, a change board — the organization decides); how they deliberate; what external tools they use; DCM records decisions, not deliberation | N members of the declared DCMGroup record decisions via the Admin API within the declared window |

### Tier Extensibility

The four default tiers (`auto`, `reviewed`, `verified`, `authorized`) are DCM system defaults. Organizations can add custom tiers by inserting them into the ordered list between existing tiers. The tier name is stable; numeric weight is derived from list position at evaluation time.

Example: An organization adds `compliance_reviewed` between `verified` and `authorized`:
```
auto → reviewed → verified → compliance_reviewed → authorized
```
All existing references to `authorized` continue to work. Only the threshold ranges in the affected profile need updating. See [Authority Tier Model](32-authority-tier-model.md).

### The `authorized` Tier — What DCM Builds vs What It Does Not Not

DCM does **not** build an authorized group management system. It does not track deliberation, run voting sessions, manage agendas, or coordinate review meetings.

DCM builds:

1. **DCMGroup membership management** — which actors constitute the authorized group; configurable by platform admins
2. **Quorum declaration** — `N of M` threshold declared in the profile or per-decision configuration
3. **Notification routing** — when a decision enters `pending_authorized` state, the notification service fires to all DCMGroup members
4. **Vote recording API** — the Admin API endpoint that authorized group members (or external systems acting on their behalf) call to record `approve` or `reject`
5. **Quorum tracking** — DCM counts votes and advances the pipeline when N is reached
6. **Audit trail** — every vote is audited with actor UUID, timestamp, decision, and the system that recorded it

External systems (ServiceNow, Jira, email workflows, Slack bots) connect to DCM by calling the vote recording API. A Slack bot that collects emoji reactions from group members and then calls DCM's Admin API is a valid implementation — DCM doesn't care how the organization collected the vote, only that an authorized group member recorded it.

### Admin API as the Integration Point

The Admin API approval endpoint is designed to be called by external systems, not only by humans in a DCM UI:

```
POST /api/v1/admin/approvals/{approval_uuid}:vote
Authorization: Bearer <token>     # any actor who is a member of the required DCMGroup

{
  "decision": "approve | reject",
  "reason": "<human-readable rationale>",
  "recorded_via": "dcm_admin_ui | servicenow | jira | slack_bot | api_direct | other",
  "external_reference": "<ticket or case ID in external system — optional>"
}

Response 200:
{
  "approval_uuid": "<uuid>",
  "voter_uuid": "<uuid>",
  "decision": "approve",
  "votes_recorded": 2,
  "quorum_required": 3,
  "quorum_reached": false,
  "pipeline_status": "pending_authorized"
}

# When quorum is reached:
{
  "approval_uuid": "<uuid>",
  "voter_uuid": "<uuid>",
  "decision": "approve",
  "votes_recorded": 3,
  "quorum_required": 3,
  "quorum_reached": true,
  "pipeline_status": "activating"
}
```

The `recorded_via` field provides the audit trail provenance — DCM knows whether the vote came through its own UI, a ServiceNow integration, a Jira plugin, or a direct API call. This is not enforced — it is informational for audit purposes.

### Deadline and Escalation

DCM manages the approval window (the time within which a decision must be reached) and fires escalation notifications when the window is approaching:

```yaml
approval_window:
  reviewed: PT72H          # 3 days; configurable per profile
  verified: PT72H
  authorized: P7D              # 7 days for deliberation; configurable
  on_expiry:
    reviewed:  escalate    # escalate to platform admin
    verified: escalate
    authorized:    reject      # authorized tier that cannot reach threshold in window → reject
```

When the window expires without a decision, DCM fires an escalation notification and either rejects (for authorized) or escalates to the next approval tier (for reviewed and verified). The organization can configure these windows to match their actual governance processes.

### DPO Alignment

The approval tier model directly implements all four design priorities:

1. **Security:** Approval tiers are the enforcement mechanism for governance. The gate is DCM's responsibility — it cannot be bypassed, and every decision is audited.
2. **Ease of use:** The Admin API as integration point means organizations use whatever workflow tools they already have. DCM does not require them to adopt a new process tool.
3. **Extensibility:** The `recorded_via` field and `external_reference` field make the approval tier model composable with arbitrary external systems without DCM needing to integrate with each one.
4. **Fit for purpose:** The tier model enables governance of every pipeline decision (request approval, policy contribution, provider registration, federation contribution) through a single consistent mechanism.

## Documentation Requirements

Every document in the DCM data model should:

1. **Reference the priority order** where design decisions are made that involve tradeoffs
2. **Explain non-negotiable security properties** with clear rationale
3. **Document what profiles control vs what they do not** for each security-relevant configuration
4. **Identify the ease-of-use mechanism** that accompanies every security requirement
5. **State fit-for-purpose scope** explicitly — what lifecycle operations does this document govern?

---

## System Policies

| Policy | Rule |
|--------|------|
| `DPO-001` | Security properties are architecturally present in all profiles. Profiles control enforcement strictness, thresholds, and automation level — not whether the property exists. |
| `DPO-002` | Every security requirement must be accompanied by an ease-of-use mechanism that makes compliance effortless for the common case. A security model routinely bypassed because of complexity has failed. |
| `DPO-003` | New capabilities should be expressed through the existing profile/policy/provider extension system before creating new mechanisms. Extensibility is achieved through composition, not proliferation. |
| `DPO-004` | Fit for purpose is a precondition, not a priority. All four priorities apply only within the constraint that the system can fulfill its lifecycle management mission. |
| `DPO-005` | The `minimal` profile is "security with minimal operational overhead" — not "minimal security." Design decisions that disable security properties rather than scaling them violate DPO-001. |
| `DPO-006` | When security and ease of use conflict, redesign the ease-of-use mechanism — not the security requirement. The secure path must also be the easy path. |

---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*

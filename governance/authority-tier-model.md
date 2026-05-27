# DCM Data Model — Authority Tier Model

**Document Status:** ✅ Complete
**Document Type:** Architecture Reference — Authority Tier Specification
**Related Documents:** [Design Priorities](00-design-priorities.md) | [Scoring Model](29-scoring-model.md) | [Federated Contribution Model](28-federated-contribution-model.md) | [Policy Profiles](14-policy-profiles.md) | [Registry Governance](20-registry-governance.md)

> **This document maps to: DATA + POLICY**
>
> The authority tier list is Data — a versioned, ordered registry entry. Tiers are referenced by name in Policies (scoring thresholds, contribution approval requirements, registration requirements). The ordered list resolves numeric weight at evaluation time.

---

## 1. The Core Model

### 1.1 What an Authority Tier Is

An authority tier declares the **required level of organizational decision gravity** for an action. It answers: "how consequential is this decision, and therefore how much authority must be engaged to approve it?"

Tiers do **not** prescribe organizational mechanisms — who satisfies a tier, how many people are involved, or what tools they use. That is entirely the organization's definition. Tiers provide the vocabulary and enforcement gate; organizations provide the substance.

### 1.2 The Ordered List

Authority tiers are defined as a **named, ordered list**. Position in the list determines numeric weight. Names are stable references used throughout the system. New tiers can be inserted anywhere without changing existing names or breaking existing references.

```yaml
authority_tier_registry:
  version: "1.0.0"
  tiers:
    - name: auto
      position: 1              # derived from list order; do not hardcode
      decision_gravity: none
      description: >
        No human judgment required. System confidence — scoring, validation,
        governance matrix checks — is sufficient to proceed. DCM activates
        automatically on pass.
      dcm_gate: All structural and governance validation checks pass
      organization_provides: Nothing — fully automated
      dcmgroup_required: false

    - name: reviewed
      position: 2
      decision_gravity: routine
      description: >
        Standard authority. A qualified reviewer in the relevant domain
        must evaluate and record a decision. Routine operational decisions
        that benefit from human oversight but do not require elevated authority.
      dcm_gate: One actor with reviewer role records a decision via Admin API
      organization_provides: >
        Who constitutes a qualified reviewer for this action type;
        the review process; recording via DCM Admin API or external system
      dcmgroup_required: false
      typical_use: Standard request approval; routine policy contributions; dev/standard provider registration

    - name: verified
      position: 3
      decision_gravity: elevated
      description: >
        Elevated authority. Two independent, distinct reviewers must each
        evaluate and record a decision. Enforces separation of duties —
        the same actor cannot satisfy both requirements. Used for decisions
        with operational or security significance requiring independent confirmation.
      dcm_gate: Two distinct actors with reviewer role each record a decision via Admin API
      organization_provides: >
        Who constitutes qualified reviewers; both review processes;
        may use external workflow tools that call the DCM Admin API
      dcmgroup_required: false
      typical_use: High-risk provider registration; elevated-score requests; significant policy changes

    - name: authorized
      position: 4
      decision_gravity: critical
      description: >
        Highest authority weight. Reserved for decisions with organizational,
        regulatory, or security consequence requiring the highest level of
        deliberate authorization. Who constitutes sufficient authority is
        entirely the organization's definition — a CTO, a CISO and legal
        counsel, a change advisory board, a single person with delegated
        authority. DCM enforces that the declared authority group engaged
        and recorded their decision; it does not prescribe the group structure
        or deliberation process.
      dcm_gate: N members of a declared DCMGroup record decisions via Admin API (quorum threshold)
      organization_provides: >
        Authority group composition (declared as a DCMGroup);
        quorum threshold (N of M); deliberation process; external tools
        (ServiceNow, Jira, Slack bots may call Admin API on behalf of members)
      dcmgroup_required: true
      typical_use: Governance matrix changes; sovereign-profile actions; credential provider registration; federation policy
```

### 1.3 Numeric Weight Resolution

The numeric weight of a tier is its **position in the ordered list**, resolved at evaluation time. It is never stored as a hardcoded number in configuration.

```
Given the default list: auto(1) → reviewed(2) → verified(3) → authorized(4)

If an organization inserts a custom tier:
  auto(1) → reviewed(2) → verified(3) → compliance_reviewed(4) → authorized(5)

DCM resolves:
  weight("reviewed")         = 2
  weight("verified")         = 3
  weight("compliance_reviewed") = 4
  weight("authorized")       = 5

All existing references to "authorized" continue to work.
No configuration changes required for existing tiers.
```

### 1.4 decision_gravity Vocabulary

`decision_gravity` is a stable, position-independent classification used by the scoring model and profile system to reason about tier severity without depending on tier names. It is declared on each tier and must be assigned when creating custom tiers.

| Value | Meaning | Default DCM tiers |
|-------|---------|------------------|
| `none` | Automated; no human judgment | `auto` |
| `routine` | Standard operational decision | `reviewed` |
| `elevated` | Significant decision; separation of duties | `verified` |
| `critical` | Highest consequence; maximum authority | `authorized` |

Organizations creating custom tiers must assign one of these four gravity values. If a future need arises for a gravity level between `elevated` and `critical`, the vocabulary can be extended — but this is a DCM-level change, not an organization-level one.

---

## 2. Custom Tier Definition

### 2.1 How Organizations Add Tiers

Organizations can extend the authority tier list by contributing custom tier definitions through the standard contribution pipeline. Custom tiers are contributed at the organization or tenant domain scope.

```yaml
custom_tier_contribution:
  name: compliance_reviewed          # unique within the deployment
  insert_after: verified             # position declaration — inserts after this tier
  decision_gravity: elevated         # must match or be consistent with position
  description: >
    Elevated authority with mandatory compliance officer sign-off.
    Required for actions affecting regulated data domains (PII, PCI, HIPAA).
    The compliance officer may be one person or a designated compliance team;
    the organization defines who satisfies this role.
  dcm_gate: One actor with compliance_officer role records a decision via Admin API
  organization_provides: >
    Who holds the compliance_officer role; compliance review process;
    may be satisfied by external GRC system calling Admin API
  dcmgroup_required: false           # single reviewer sufficient at this gravity
  applicable_profiles: [standard, prod, fsi, sovereign]
  contribution_requires: verified    # adding a custom tier requires verified-tier approval
```

### 2.2 Contribution Approval Requirements

Custom tier contributions require `verified` tier approval (two independent reviewers) because they affect all pipeline decisions in the deployment. An organization cannot unilaterally add a tier that demotes an existing gravity level or bypasses the `authorized` tier for critical decisions.

**Constraints on custom tiers:**
- `decision_gravity` must be consistent with position (a tier inserted before `reviewed` cannot have `critical` gravity)
- Custom tiers cannot be inserted before `auto` or after the highest `critical` gravity tier
- A custom tier with `dcmgroup_required: true` must declare a valid DCMGroup at contribution time
- Custom tiers cannot change the `dcm_gate` semantics of existing DCM tiers

### 2.3 External Tier Registries

For federation deployments, peer DCM instances may have different custom tier lists. When a federated request requires approval from a peer's tier, DCM resolves the equivalent gravity level from the local list:

```yaml
federation_tier_resolution:
  strategy: gravity_match            # match by decision_gravity, not tier name
  on_unknown_tier: escalate_to_gravity  # if peer tier unknown, use its declared gravity
  fallback_tier: authorized          # if gravity unknown, apply highest local tier
```

---

## 3. Profile Threshold Configuration

### 3.1 Dynamic Threshold Format

Profile approval thresholds are expressed as a named-tier list, not fixed column headers. This allows the threshold table to accommodate custom tiers without restructuring.

```yaml
# Standard profile — default DCM tiers
approval_routing:
  thresholds:
    - tier: auto
      max_score: 24          # score 0–24: auto-approve
    - tier: reviewed
      max_score: 59          # score 25–59: reviewed tier required
    - tier: verified
      max_score: 79          # score 60–79: verified tier required
    - tier: authorized
      max_score: 100         # score 80–100: authorized tier required

# Organization adds compliance_reviewed between verified and authorized
approval_routing:
  thresholds:
    - tier: auto
      max_score: 24
    - tier: reviewed
      max_score: 59
    - tier: verified
      max_score: 74          # adjusted to make room
    - tier: compliance_reviewed
      max_score: 84          # new tier occupies this range
    - tier: authorized
      max_score: 100         # unchanged name; adjusted range
```

### 3.2 Default Profile Thresholds

```yaml
profile_approval_thresholds:
  minimal:
    - { tier: auto,       max_score: 44 }
    - { tier: reviewed,   max_score: 100 }

  dev:
    - { tier: auto,       max_score: 39 }
    - { tier: reviewed,   max_score: 69 }
    - { tier: verified,   max_score: 100 }

  standard:
    - { tier: auto,       max_score: 24 }
    - { tier: reviewed,   max_score: 59 }
    - { tier: verified,   max_score: 79 }
    - { tier: authorized, max_score: 100 }

  prod:
    - { tier: auto,       max_score: 14 }
    - { tier: reviewed,   max_score: 49 }
    - { tier: verified,   max_score: 74 }
    - { tier: authorized, max_score: 100 }

  fsi:
    - { tier: auto,       max_score: 9 }
    - { tier: reviewed,   max_score: 39 }
    - { tier: verified,   max_score: 69 }
    - { tier: authorized, max_score: 100 }

  sovereign:
    - { tier: auto,       max_score: 4 }
    - { tier: reviewed,   max_score: 29 }
    - { tier: verified,   max_score: 59 }
    - { tier: authorized, max_score: 100 }
```

### 3.3 SMX-008 in the Dynamic Model

SMX-008 (auto_approve_below ≤ 50) remains a hard constraint. In the dynamic model: the `auto` tier's `max_score` may never exceed 50 in any profile, regardless of custom tier additions. This constraint applies to the `auto` tier specifically, not to named thresholds.

---

## 4. Tier Evaluation in the Pipeline

### 4.1 How DCM Resolves the Required Tier

At request evaluation time, DCM:

1. Computes the request risk score (0–100) from the scoring model
2. Loads the active profile's threshold list
3. Walks the list in order; the first tier whose `max_score ≥ risk_score` is the required tier
4. Resolves the numeric weight of the required tier from the ordered tier list
5. Creates an approval record with the required tier name and weight

The tier name — not the weight — is what is stored in the approval record and what reviewers see. The weight is used for comparison operations (e.g., "is this action at least as significant as `verified`?").

### 4.2 Approval Record

```yaml
approval_record:
  approval_uuid: <uuid>
  subject_uuid: <uuid>
  subject_type: request | policy_contribution | provider_registration | federation_contribution
  required_tier: verified           # tier name — stable reference
  required_tier_weight: 3           # resolved at creation; stored for point-in-time audit
  required_tier_gravity: elevated
  dcmgroup_uuid: <uuid | null>      # non-null only for dcmgroup_required: true tiers
  quorum_threshold: <N | null>
  status: pending_reviewed | pending_verified | pending_authorized | pending_<custom_tier>
  created_at: <ISO 8601>
  window_expires_at: <ISO 8601>
  decisions: []
```

---

## 5. DCMGroup Assignment for Authorized Tier

When a decision requires the `authorized` tier (or any custom tier with `dcmgroup_required: true`), the required DCMGroup and quorum threshold must be declared. This is configured in the profile or per-action-type:

```yaml
authorized_tier_configuration:
  default_dcmgroup_handle: platform/security-council   # default group for authorized decisions
  quorum_threshold: "2 of 5"                           # N of M
  
  # Per-action-type overrides
  action_type_overrides:
    - subject_type: provider_registration
      provider_type: service_provider
      dcmgroup_handle: platform/credential-governance
      quorum_threshold: "3 of 5"
    - subject_type: federation_contribution
      dcmgroup_handle: platform/federation-council
      quorum_threshold: "2 of 3"
    - subject_type: policy_contribution
      policy_domain: system
      dcmgroup_handle: platform/policy-governance
      quorum_threshold: "3 of 5"
```

Organizations define the DCMGroup membership. DCM enforces that the declared group and quorum were satisfied.

---

---

## 7. Tier Registry Change Impact Detection

When the authority tier registry is modified — a new tier inserted, a tier removed, a tier's `decision_gravity` changed, or a tier's position changed — DCM must evaluate the impact on all items that reference tier names before activating the change. This section specifies the detection model.

> **Implementation note:** The impact detection pipeline described here is a required implementation component, not an optional audit feature. A tier registry change that creates security degradations must not activate until each degradation is explicitly acknowledged by a reviewer at `verified` tier or above. The detection mechanism itself is an implementation detail; this specification defines the required behavior and data model.

### 7.1 Tier Impact Diff

Before activating a tier registry change, DCM computes a **tier impact diff** by comparing the proposed ordered list to the current ordered list.

```yaml
tier_impact_diff:
  registry_change_uuid: <uuid>
  proposed_at: <ISO 8601>
  proposed_by: <actor_uuid>
  
  tier_changes:
    - tier_name: verified
      change_type: POSITION_CHANGED    # NEW | REMOVED | POSITION_CHANGED | GRAVITY_CHANGED | UNCHANGED
      old_position: 3
      new_position: 4                  # something inserted before it
      old_gravity: elevated
      new_gravity: elevated            # gravity unchanged
      net_effect: UPGRADED             # higher position = more weight = more scrutiny required
      
    - tier_name: compliance_reviewed   # newly inserted
      change_type: NEW
      old_position: null
      new_position: 3
      old_gravity: null
      new_gravity: elevated
      net_effect: NEW
      
    - tier_name: authorized
      change_type: POSITION_CHANGED
      old_position: 4
      new_position: 5
      old_gravity: critical
      new_gravity: critical
      net_effect: UPGRADED

  security_degradations: []           # list of DEGRADED tier changes
  profile_gaps: []                    # profiles whose threshold list is incomplete after change
  broken_references: []               # tier names referenced in config that no longer exist
```

**Net effect classification:**

| Net Effect | Condition | Risk |
|-----------|-----------|------|
| `UPGRADED` | Tier's position increased (higher weight) OR gravity increased | None — more scrutiny required than before |
| `DEGRADED` | Tier's position decreased (lower weight) OR gravity decreased | **Security risk** — items referencing this tier now have lower effective authority requirement |
| `NEW` | Tier inserted into registry | Low — no existing references; profile gap detection applies |
| `REMOVED` | Tier deleted from registry | **Broken references** — any item referencing this tier name is now unresolvable |
| `UNCHANGED` | Position and gravity identical | None |

### 7.2 Affected Item Query

After computing the tier impact diff, DCM queries for all items affected by each changed tier:

```
Affected item categories:

PENDING APPROVAL RECORDS
  Query: approval_records WHERE required_tier IN (changed_tier_names) AND status LIKE 'pending_%'
  Impact: The tier name is stable; the weight at which the item was queued may differ from
          the current weight. Compare stored_tier_weight (ATM-008) vs current_tier_weight.
  
PROFILE THRESHOLD CONFIGURATIONS
  Query: all profiles WHERE tier_registry_version < new_registry_version
  Impact: Profiles whose threshold list doesn't include newly added tiers have a gap —
          requests that score into the new tier's range will fall back to the adjacent tier.
          Flag as PROFILE_GAP; notify platform admin to update threshold list.

PROVIDER REGISTRATION REQUIREMENTS
  Query: provider_type_registry WHERE default_approval_method IN (changed_tier_names)
         AND profile_registration_policy WHERE min_approval_method IN (changed_tier_names)
  Impact: If the referenced tier's gravity decreased, the minimum requirement is now lower.

FCM CONTRIBUTION POLICY REQUIREMENTS  
  Query: contribution_policy WHERE any tier reference IN (changed_tier_names)
  Impact: Same as provider registration — if gravity decreased, requirement is lower.

ACTIVE POLICY SETS
  Query: active_policies WHERE policy_content CONTAINS tier_name_reference
  Impact: Policies that reason about tiers by name should be using dynamic resolution.
          If a policy hardcodes a tier weight, it may now be stale.
          Flag for policy owner review.
```

### 7.3 Impact Classification

Each affected item receives one or more impact classifications:

| Classification | Condition | Required Action |
|---------------|-----------|----------------|
| `SECURITY_DEGRADATION` | Item references a tier whose gravity decreased OR position decreased | **Blocks activation** — must be reviewed and accepted |
| `SECURITY_UPGRADE` | Item references a tier whose gravity or position increased | Informational — logged and reported; does not block |
| `BROKEN_REFERENCE` | Item references a tier name that no longer exists in registry | **Blocks activation** — must be resolved (tier restored, item updated, or item cancelled) |
| `PROFILE_GAP` | Profile threshold list incomplete after new tier insertion | **Warning** — does not block activation; platform admin must update thresholds or acknowledge gap |
| `STALE_WEIGHT` | Pending approval record's `stored_tier_weight` differs from current weight for same tier name | Informational — logged; record remains valid since tier name is stable |

### 7.4 Degradation Review Gate

Security degradations block tier registry activation. The blocking gate requires:

1. Each `SECURITY_DEGRADATION` item is presented to a reviewer at `verified` tier or above
2. The reviewer records an explicit acceptance decision for each degradation via the Admin API
3. The acceptance includes a reason and is written to the audit trail
4. Only after all degradations are accepted does the tier registry change activate

This is the same pattern as the standard approval pipeline — DCM provides the gate; the organization provides the review process. The difference is that the required tier for the degradation review is always at least `verified`, regardless of the profile in use.

```
POST /api/v1/admin/tier-registry/{change_uuid}:accept-degradation

{
  "affected_item_uuid": "<uuid>",
  "affected_item_type": "provider_registration_requirement",
  "degradation_classification": "SECURITY_DEGRADATION",
  "acceptance_reason": "<required — what compensating controls exist>",
  "accepted_by": "<actor_uuid>"       # must be verified-tier or above reviewer
}
```

Broken references cannot be accepted — they must be resolved. DCM will not activate a tier registry change that leaves unresolvable tier references.

### 7.5 Impact Report

Whether or not the change requires a degradation review gate, DCM generates a tier registry impact report at proposed time and again at activation time:

```yaml
tier_registry_impact_report:
  registry_change_uuid: <uuid>
  report_generated_at: <ISO 8601>
  stage: proposed | accepted | activated

  summary:
    degradations: 0
    upgrades: 3
    new_tiers: 1
    broken_references: 0
    profile_gaps: 2
    stale_weight_records: 4

  degradations: []

  upgrades:
    - affected_item_uuid: <provider_registration_requirement_uuid>
      affected_item_type: provider_registration_requirement
      tier_name: verified
      old_weight: 3
      new_weight: 4
      old_gravity: elevated
      new_gravity: elevated
      impact: "Effective authority requirement is higher — more scrutiny now required"

  profile_gaps:
    - profile: standard
      missing_tiers: [compliance_reviewed]
      gap_effect: >
        Requests scoring between the verified and authorized thresholds will route
        to verified tier until the profile threshold list is updated to include compliance_reviewed

  notification_targets:
    - platform_admin
    - provider_owners       # for SECURITY_DEGRADATION items
    - affected_actor_groups # DCMGroup members for authorized-tier items
```

The impact report is stored in the Audit Store and is linked to the tier registry version. Platform admins can query historical impact reports to understand what changed and when.

### 7.6 Audit Trail Requirements

Every tier registry change produces the following audit records, regardless of whether degradations exist:

- Registry change proposal record (who proposed, what changed, when)
- Tier impact diff record (all tier changes, all affected items, all classifications)
- Per-degradation acceptance records (if any degradations exist)
- Registry activation record (actual effective timestamp)
- Per-affected-item notification records (who was notified, when)

Historical approval records retain their `stored_tier_weight` from time of creation (ATM-008). The audit trail thus contains both the point-in-time weight (what authority level was required when the decision was made) and the current weight (what authority level the same tier name requires today), enabling auditors to identify decisions made under different governance regimes.

### 7.7 System Policy Additions

| Policy | Rule |
|--------|------|
| `ATM-009` | A tier registry change that produces one or more `SECURITY_DEGRADATION` items must not activate until each degradation is explicitly accepted by a reviewer at `verified` tier or above. |
| `ATM-010` | A tier registry change that produces one or more `BROKEN_REFERENCE` items must not activate. Broken references must be resolved before the change can proceed. |
| `ATM-011` | Every tier registry change must produce a tier impact report. The report is stored in the Audit Store and linked to the registry version. |
| `ATM-012` | Profile threshold lists that become incomplete after a tier registry change (PROFILE_GAP) generate a warning notification to platform admins. The change may activate; platform admins must update threshold lists or explicitly acknowledge the gap within the profile's approval window. |

## 6. System Policies

| Policy | Rule |
|--------|------|
| `ATM-001` | Authority tiers are identified by name, not numeric weight. Numeric weight is resolved from list position at evaluation time and is never hardcoded in configuration. |
| `ATM-002` | The `auto` tier's `max_score` threshold may never exceed 50 in any profile (SMX-008 translated to dynamic model). |
| `ATM-003` | Custom tiers must declare `decision_gravity` consistent with their position in the ordered list. A tier with lower gravity may not be inserted after a tier with higher gravity. |
| `ATM-004` | Custom tier contributions require `verified` tier approval. Organizations cannot add tiers unilaterally. |
| `ATM-005` | Custom tiers cannot alter the `dcm_gate` semantics of existing DCM system tiers (`auto`, `reviewed`, `verified`, `authorized`). |
| `ATM-006` | For tiers with `dcmgroup_required: true`, the DCMGroup and quorum threshold must be declared in the profile configuration before the tier can be used as a routing target. |
| `ATM-007` | The four default `decision_gravity` values (`none`, `routine`, `elevated`, `critical`) are DCM system vocabulary. New gravity values require a DCM-level change, not an organization-level contribution. |
| `ATM-008` | Approval records store the tier name and the resolved weight at creation time. If the tier list changes after an approval record is created, the stored weight reflects the state at creation (point-in-time audit). |
| `ATM-009` | A tier registry change that produces one or more `SECURITY_DEGRADATION` items must not activate until each degradation is explicitly accepted by a reviewer at `verified` tier or above. |
| `ATM-010` | A tier registry change that produces one or more `BROKEN_REFERENCE` items must not activate. Broken references must be resolved before the change can proceed. |
| `ATM-011` | Every tier registry change must produce a tier impact report stored in the Audit Store and linked to the registry version. |
| `ATM-012` | `PROFILE_GAP` conditions generate a warning notification to platform admins. The change may activate; admins must update threshold lists or explicitly acknowledge the gap within the profile's approval window. |

---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*

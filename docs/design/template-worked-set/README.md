# Template — the worked set

Eight files, one story: the same three-tier application expressed at every tier, plus the Workflow
category, plus the negative set that decides whether any of it is real.

**These are drafts, deliberately outside the registry.** Four decisions are still open and dropping
half-designed classes into `registry/` would break the path, coverage, and traceability gates. Nothing
here is committed.

| File | Tier | What it demonstrates |
|---|---|---|
| `01-class-base-template.yaml` | base | the mechanism only — **no constituents** |
| `02-class-type-template-application.yaml` | type | the **category of service**; the GUI nav; `context` |
| `03-class-provider-template-application-acme.yaml` | provider | the **concrete composition**; `supports`; opinions |
| `04-catalog-item-projection.yaml` | catalog | where **tenancy** enters; derived, not authored |
| `05-system-realized.yaml` | instance | `tenant_uuid` · `sovereignty` · the edges |
| `06-class-type-template-workflow.yaml` | type | the **terminal-yield** category |
| `07-class-provider-workflow-shutdown.yaml` | provider | #330 — your converged-host shutdown |
| `08-what-must-fail.yaml` | — | nine refusals; **3 of 9 are gated today** |

## The ladder

```
base      Template                                    mechanism. no constituents. no values.
type      Template.Application | Template.Workflow    category of service. GUI nav. context.
provider  Template.Application.AcmeThreeTier          the composition. supports. opinions legal.
catalog   acme/catalog/three-tier-web-app             DCM projection: per-org curation + tenancy
instance  appteam/shop-prod                           the System. tenant_uuid, sovereignty, edges.
```

Two independent rules force the concrete composition to the **provider** tier, and it is worth
noticing that they agree:

- `class.schema.json` — constituents are *"permitted on type and provider tiers, **never base**"*
  (your ruling, 2026-08-03). Zero classes use the property today.
- **NDF-001 / rule 41** — a concrete template carries opinions (`postgresql`, `replicas: 2`, a pinned
  image). An opinion is legal at exactly one tier, because *"a provider IS an opinionated
  implementation."*

The consequence to state out loud in the ADR: **"provider" here means *authoring authority*** — a
platform team — not an infra provider. The word currently reads as OCPVirt/AWS.

## Where your three paradigms actually land

| | Base | Type | Provider | Catalog | System |
|---|---|---|---|---|---|
| **Tenancy** — the border | — | — | — | owner + `offered_to` + authorization | `tenant_uuid`, one, required |
| **Namespace** — grouping, no isolation | shape of `groupings` | — | values | `acme/…` handle prefix | derived membership |
| **Sovereignty** — constraint + guidance | shape of the floor | — | the floor's value | surfaced to the consumer | realized + attested |

Class tiers carry **none** of it, and that is already the model's line:
*"Definitions are universal … usage constraints live at the instance level. Definitions are the
public dictionary; instances are the private documents written with it."*

## The invariant that decides the shape

> **GRP-INV-002** — Constituent relationships may not cross tenant_boundary group boundaries.
> Non-overridable, regardless of profile or enforcement model.

So **a `contained_by` constituent must be co-tenant; anything cross-tenant is an edge.** That turns
ADR-033's containment-vs-binding distinction from a modelling preference into a structural law, and
it decides three things at once:

- the platform namespace and the shared VLAN are **stakes**, not parts (`05-`, `dependencies`)
- a bound activity — the nightly backup — is an edge, which is also why it survives the stack's
  decommission instead of being torn down in reverse-topological order with it
- the #330 shutdown workflow owns **nothing**: it operates on an estate that outlives it (`07-`)

**And here is the gap in one line.** `realized-entity.dependencies` already carries
`edge_type: depends_on | references | contained_by | binds_to`. `catalog-item.constituents` carries
no edge type at all — every constituent is implicitly containment.

> **The Template cannot declare what the System is required to record.**

Every `edge:` key in `03-` and `07-` is marked ⚠️ for that reason. It is the one addition the rest
of this depends on.

## Sovereignty is where a composite stops being a bag of parts

`cohesion: same_zone` is the element that does not exist anywhere. Without it, a three-tier app whose
database lands in `eu-central-sovereign` and whose web tier lands in `eu-west-sovereign` passes every
gate: each zone accredited, each classification satisfied, each `plane_attestation` verified — and
the composite is still a breach. See `08-`, case 3.

It is also the sharpest argument for your loop ordering. A joint constraint can only be evaluated
once every placement is known, and a failure has to **re-place** — which is another iteration, not a
post-placement correction. Placement had to be inside the loop.

**Watch this:** `07-`'s `serialize_on` — don't stop the next converged host until Ceph is back to
`HEALTH_OK` — is the *same shape*. A constraint over a set, evaluated when the set is known. Two
findings arrived at it independently from opposite directions. Build it once.

Blocked on **#385** for the zone vocabulary either way.

## What the four #405 orphans became

| Orphan | Lands as |
|---|---|
| `replicas` | **cardinality on a constituent** — where it was always trying to be |
| `high_availability` | an element of the composition (today it is a `spec_default` set onto a field `Data.Database` does not have) |
| `environment` | a layer selector — not template data |
| `domain` | a `Network.DNSZone` reference |

`consumer_fields` is gone: the option list **is** `supports`, read directly (`04-`,
`offered_selections`). `spec_defaults` is gone from the item and lives on the provider class, where
it is legal and carries an author.

## Open decisions

1. **`edge:` on a constituent** — this is the load-bearing addition. Confirm before anything else.
2. **The type tier may also carry constituents.** A *category* has none. A **Pattern** — abstract
   slots naming capabilities rather than classes — would use exactly that, and the ruling permits it.
   Is a Pattern a type-tier class with abstract constituents, or a record? I did not choose for you;
   `02-` shows the category reading only.
3. **`ownership_model`** — in the ownership doc's examples, in zero schemas. Making constituent
   ownership checkable needs it declared.
4. **Does a Workflow inherit the sovereignty of what it touches?** May an operator in one zone run a
   workflow against a System in another? ADR-057 says UDLM carries the requirement and the Matrix
   decides; nothing says whether the requirement attaches to the run or only to its targets.

## Drive-bys found while building this

- `registry/dcm-group.schema.json` **does not exist**; `realized-entity` and `catalog-item` cite it
  in 3 places. It was replaced by `Access.Grouping` and the pointers were never updated —
  `tenant_uuid`'s own description points at a missing file.
- The `Job` class cites **ENT-004** for mandatory `max_execution_time`, twice. It is **ENT-002**;
  ENT-004 is composite health.

# One record per state

**What this is:** a proposal to store each of an entity's four states as its own record, instead
of one record that carries all four inside it. It settles what a record is, what a realized
record must contain so it can be used on its own, and what the shared identity is. It is written
for review; the decisions it needs are at the end.

**Status:** research. Nothing here is applied. This is a separate program from the class-tier
series and should not be folded into it.

## The problem in plain words

Today one instance record holds everything that ever happened to the entity: what the consumer
asked for, what policy turned that into, what the provider built, and what discovery last saw.
They sit side by side under `states.intent`, `states.requested`, `states.realized`, and
`states.discovered`, in a single document with a single identity.

That means four different parties write one document. The consumer writes intent. The control
plane writes requested. The provider writes realized. Discovery writes discovered. The schema
has an `ownership` block whose whole job is to arbitrate between those writers, which is a sign
the shape is wrong: a record with one author does not need one.

It also means a realized record cannot be handed to anyone on its own. A load balancer that
wants the VM's addresses, a DR runbook that wants to rebuild the VM exactly, an inventory tool
that wants what exists: each gets the intent and the policy history along for the ride. And any
change to any state rewrites the whole document, so the realized record's version history is
tangled with the intent's.

## The spec already says the states are separate

This is not a new design. `four-states.md` stores the states apart and has since the beginning:

| State | Where the spec stores it | What the spec says about it |
|---|---|---|
| Intent | Commit Log | append-only, immutable, the consumer's declaration never modified |
| Requested | State Store | append-only, immutable, a new record per request cycle |
| Realized | State Store | write-once complete snapshots, each traceable to exactly one requested record, each carrying a supersession chain to the one before and the one after |
| Discovered | Discovered stream | append-only, refreshed per discovery run |

The one thing they share is the entity UUID, which the spec calls the universal linking key.
Rehydration (four-states.md §5.1) starts from any one of the three stored states on its own.
Data-model-core ruling D1 defines those four stores by contract. The commit-log entry schema
already has the shape this brief proposes: an `entry_uuid` for the record and an `entity_uuid`
for the thing it is about.

## The schema does something else

`registry/realized-entity.schema.json` describes itself as "the operational record of one entity
as it flows through the four states" and folds all four into one document. Twelve worked
examples in `registry/examples/` follow it. `validate.py` and four gates read `states.realized`
or `states.requested` out of that one document. Nothing says it is a view over the stores; it is
treated as the record.

So the spec and the schema disagree, and the schema is the one to correct.

## What one record per state buys

- **A realized record stands alone.** It carries what the provider built, the outputs other
  things bind to, health, placement, and the natural keys discovery uses to recognize it. A
  consumer reads it without the intent or the policy trail.
- **One author per record.** Intent is the consumer's. Requested is the control plane's.
  Realized is the provider's. Discovered is discovery's. No arbitration, no `ownership` block.
- **Rehydration reads the right record.** Replay from intent to pick up current standards, from
  requested to reproduce the approved spec, from realized to rebuild exactly. Each is a record,
  not a slice of one.
- **Version history per state.** A new intent does not rewrite the realized record. The
  supersession chain the spec already asks for on realized snapshots becomes literal: each record
  names the one it replaced.
- **Drift is a comparison, not a field.** Compare the latest realized record with the latest
  discovered record. The spec describes drift this way already; the schema stores it as a block.

## The proposal

Every state record shares one envelope and adds one payload.

**The envelope**, identical on all four:

| Field | Meaning |
|---|---|
| `entity_uuid` | the thing this record is about; stable for life; what every edge points at |
| `record_uuid` | this record; time-ordered so a stream sorts itself |
| `state` | intent, requested, realized, or discovered |
| `generation` | which request cycle this belongs to |
| `supersedes` | the `record_uuid` of the record this one replaced, or null for the first |
| `tenant_uuid`, `resource_type`, `type_version`, `type_ref` | as today |
| `integrity` | the record's own chain link, as ADR-059 already requires per version |

**The payloads:**

| State | Carries | Author |
|---|---|---|
| Intent | `fields` as written; provenance for those fields | the consumer |
| Requested | `fields` after assembly and policy; `assembly`; provenance for what policy and layers set; `intent_ref` | the control plane |
| Realized | `fields` as built; `outputs`; `provider` as a typed reference to the provider instance, not free text; `status`; `sovereignty`; `correlation_ids`; `adopted_standards`; `portability`; provenance for what the provider set; `requested_ref` | the provider |
| Discovered | `fields` and `outputs` as observed; `observed_at`; `correlation_ids` | discovery |

`dependencies` belong on requested (as resolved by placement) and realized (as confirmed).
`drift` and `ownership` go away as stored fields. `expected_observation` stays on realized,
since it is a declared expectation about that realization.

**The merged view survives as a read model.** A dashboard or a human still wants "show me this
entity", assembled from the latest record of each state. That is a query result, never something
written. If the current schema is kept for that purpose it should be renamed to say so.

## The same VM, as a realized record

Yesterday's example, cut down to what the provider actually owns:

```yaml
entity_uuid: 2f7c9a41-8e3d-4b6a-9c15-7d2e4f8a1b03
record_uuid: 019215a8-6c3e-7d2b-9f41-3a8c5e7b2d90
state: realized
generation: 1
supersedes: null
requested_ref: 019215a8-2b1d-7c4a-8e33-6f2a9d4c1b77
tenant_uuid: 75ccf4ff-3e8d-4963-bc51-459ae1014cb7
resource_type: Compute.VM
type_version: 1.5.4
type_ref: https://udlm.dev/registry/udlm/0.1/class/Compute.VM/1.5.4
provider: lab/providers/libvirt-host-a
at: "2026-09-03T14:03:40Z"
time_source: provider-callback

fields:
  cpu: {count: 4, sockets: 1, cores_per_socket: 4}
  memory: {size: 16Gi}
  guest_os: uuid/6b1f2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d@1?reference_data_type==os_image
  firmware: {type: uefi, secure_boot: true, vtpm: false}
  networks: [{name: eth0, vlan: lab/net/vlan-20, network_ref: lab/net/dmz}]
  layout_ref: lab/storage/layout/app-01
  placement: {location_ref: lab/facility/rack-3}
  run_state: {desired_state: running}

outputs:
  ip_addresses: ["192.0.2.55"]
  primary_ip: "192.0.2.55"
  hostname: app-01.lab.example
  mac_addresses: ["52:54:00:ab:12:34"]
  provider_handle: app-01
  observed_run_state: running

dependencies:
  - {edge_type: contained_by, target_uuid: 8a4d1e6f-2b3c-4d5e-9f0a-1b2c3d4e5f60, target_handle: lab/host/host-a, strength: hard}
  - {edge_type: depends_on, target_uuid: 9f1b3d5e-7a8c-4b0d-9e4f-8b0c2d4e6a71, target_handle: lab/storage/vol/app-01-root, strength: hard}
  - {edge_type: depends_on, target_uuid: a1c3e5f7-9b0d-4c2e-8f6a-0c2d4e6a8b93, target_handle: lab/net/ip/192.0.2.55, target_field: address, bound_field: outputs.primary_ip, strength: hard}

correlation_ids:
  - {scheme: libvirt-domain-uuid, value: 4e2a7c19-6b3d-4f8e-a1c5-9d0b2e7f3a64}
  - {scheme: mac, value: "52:54:00:ab:12:34"}

status:
  state: Running
  conditions: [{type: Ready, status: "True", reason: GuestAgentConnected}]

sovereignty: {zone: us-mn, classification: internal, locality: {fault_domain: rack-3/host-a}}
portability: {classification: portable, portability_breaking: false}

provenance:
  outputs.ip_addresses: [{source: {kind: provider, id: lab/providers/libvirt-host-a}, operation_type: set, timestamp: "2026-09-03T14:03:40Z"}]
  outputs.mac_addresses: [{source: {kind: provider, id: lab/providers/libvirt-host-a}, operation_type: set, timestamp: "2026-09-03T14:03:40Z"}]

integrity: {head: "sha256:8b2d…2b4d", previous: null, algorithm: sha256-jcs}
```

Everything the consumer or policy set lives in the intent and requested records, reachable
through `requested_ref`. Strip `outputs`, `provider`, `provider_handle` and the correlation ids,
and `fields` is a valid new intent: that is the rebuild path.

## This is how Kubernetes does it

| Kubernetes | Here |
|---|---|
| `metadata.uid` | `entity_uuid` |
| `resourceVersion` | `record_uuid` |
| `spec` as the client wrote it | intent record |
| `spec` after admission and defaulting | requested record |
| `status`, written through its own subresource | realized record |
| `metadata.generation` and `status.observedGeneration` | `generation` on requested and on realized |
| `kubectl get -o yaml`, then `kubectl apply` | a realized record's `fields`, stripped, submitted as intent |

## What changes

| Surface | Today | After |
|---|---|---|
| `registry/realized-entity.schema.json` | one schema, four folded states | four record schemas sharing one envelope; the merged shape kept only as a named read-model schema, or removed |
| `registry/examples/` | 12 examples in the folded shape | each becomes one intent record and one realized record, or is trimmed to the state it demonstrates |
| `registry/tools/validate.py` and 4 gates (`check_grant_derivation`, `check_group_invariants`, `check_offer_collapse`, `check_sovereignty_zones`) | read `states.realized` from one document | read the realized record, or the view assembled from the stores |
| 16 spec, flow and guide documents that name the schema | describe the folded record | describe the four records; `four-states.md` needs least change since it already says this |
| DCM control plane | reads and writes the folded record | writes one record per state transition; reads by entity and state |

## What does not change

The entity UUID and every edge that points at it. The four stores and their contracts. The
integrity chain, which already works per version and now works per record. The audit store.
Field-level provenance, which just splits along author lines. The class model and everything
in the class-tier series.

## Decisions for review

- **D1 — the identity of a record.** `record_uuid` as a time-ordered UUID (v7), with
  `entity_uuid` staying the stable v4. Data-model-core already reserves v7 for time-ordered
  identifiers.
- **D2 — the merged view.** Keep the current schema, renamed as an explicit read model that is
  assembled and never written, or drop it and let readers compose. I lean keep-and-rename, since
  humans and dashboards will ask for it, and a schema for a query result is still useful.
- **D3 — how to record the decision.** The spec already decided this; the schema is a defect
  against it. A register row and a schema PR, not a new ADR.
- **D4 — sequencing.** The DCM control plane writes this record, so the change is coordinated
  across the UDLM and DCM boundary and lands after the class-tier series, not interleaved with it.
- **D5 — `ownership`.** Drop it. One author per record removes the need. If a case appears where
  two providers legitimately write one realized record, that is a finding, not a field.

## Out of scope

The class model, the Base and Type definitions, and the four stores' contracts. Retention windows
on the discovered stream. How DCM implements the write paths.

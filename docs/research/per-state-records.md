# One record per state

**What this is:** a proposal to keep four records for each thing we manage, one per lifecycle
state, instead of one record that carries all four inside it. It settles what a record is, what
the record of "what got built" must contain so it can be used on its own, and what the four
records share. It is written for review, and the decisions it needs are at the end.

**Status:** research. Nothing here is applied. This is a separate piece of work from the
class-tier series and should not be folded into it.

## The problem

When someone orders a VM, we keep a single record for it. Inside that one record sit four
different things: what the person asked for, what the system turned that into after applying
policy, what the provider actually built, and what we last saw when we went and looked. Four
different parties each own a part of that one record.

That causes three problems.

Four writers on one document means we need referee rules for who may change what. The schema
has a block for exactly that purpose, and its existence is the sign that the shape is wrong: a
record with one author does not need a referee.

Nobody can be handed just "what got built". A load balancer that wants the VM's addresses, a
rebuild job that wants to recreate the VM exactly, an inventory tool that wants to know what
exists: each of them gets the order and the policy history stapled on.

And any time any of the four parts changes, the whole record changes. The history of what was
built gets tangled with the history of what was asked for.

## We already decided this. The schema didn't follow.

The four-states specification has stored the states apart from the beginning. The order goes in
the commit log, immutable. The approved version goes in the state store, a new one per request
cycle. What got built goes in the state store too, write-once, each one pointing at the exact
approved version it came from and at the one it replaced. What was observed goes in its own
stream. The only thing they share is the entity's ID, which the spec calls the universal linking
key. Rebuilding something starts from any one of the three stored states on its own.

The instance schema does something else. It describes itself as the record of one entity "as it
flows through the four states" and puts all four inside one document. Twelve worked examples
follow it. The validator and four checks read the built state out of that one document. Nothing
calls it a view over the stores; everything treats it as the record.

So the spec and the schema disagree, and the schema is the one to correct. This is not a new
decision.

## What four records buy

- **"What got built" stands alone.** It carries what the provider made, the outputs other things
  connect to, health, where it landed, and the fingerprints a discovery scan uses to recognize it.
  A consumer reads it without the order or the policy trail.
- **One author per record.** The order is the consumer's. The approved version is the system's.
  What got built is the provider's. What was observed is the scanner's. No referee.
- **Rebuilding reads the right record.** Replay the order to pick up current standards. Replay the
  approved version to reproduce what was signed off. Replay what got built to recreate it exactly.
  Each is a record, not a slice of one.
- **Each state has its own history.** A new order does not rewrite the record of what got built.
  Each record names the one it replaced, which the spec already asks for.
- **Drift is a comparison, not a box.** Put the latest "built" record next to the latest
  "observed" record and diff them. The spec already describes drift this way.

## The proposal

Every record shares one wrapper and adds one body.

**The wrapper**, the same on all four:

| Field | Plain meaning |
|---|---|
| `entity_uuid` | the thing this record is about; never changes; what every relationship points at |
| `record_uuid` | this particular record; time-ordered, so a stream of them sorts itself |
| `state` | order, approved, built, or observed (intent, requested, realized, discovered) |
| `generation` | which request cycle this belongs to |
| `supersedes` | the record this one replaced, or nothing for the first |
| `tenant_uuid`, `resource_type`, `type_version`, `type_ref` | who owns it and what kind of thing it is, as today |
| `integrity` | the record's own tamper-evidence link, as already required per version |

**The bodies:**

| State | What it carries | Who writes it |
|---|---|---|
| Order (intent) | the fields as written, and who wrote each one | the consumer |
| Approved (requested) | the fields after assembly and policy, what policy and layers filled in, and a pointer to the order | the control plane |
| Built (realized) | the fields as built; the outputs; which provider instance built it, as a proper reference rather than free text; health; placement; the fingerprints for recognition; standards negotiated; how portable it ended up; and a pointer to the approved version | the provider |
| Observed (discovered) | the fields and outputs as seen, when they were seen, and the fingerprints | discovery |

Relationships to other things belong on the approved record, as placement resolved them, and on
the built record, as the provider confirmed them. The stored "drift" and "ownership" blocks go
away. The declared expectation of how often the thing should be observed stays on the built
record, since it is a statement about that realization.

**The combined view survives as something you read, not something you write.** A dashboard or a
person will still ask "show me this entity", meaning the latest of each of the four. That is a
query result assembled from the stores. If the current schema is kept for that purpose it should
be renamed to say so.

## The same VM, as a "built" record

The libvirt VM from the class-tier discussion, cut down to what the provider actually owns:

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

Everything the consumer or policy decided lives in the order and approved records, one pointer
away. Take this record, drop the outputs, the provider, the provider's handle and the
fingerprints, and what is left is a valid new order. That is how a rebuild works.

## Kubernetes does it this way

| Kubernetes | Here |
|---|---|
| the object's `uid` | the entity ID |
| `resourceVersion` | the record ID |
| the spec as the client wrote it | the order |
| the spec after admission and defaulting | the approved version |
| the status, written through its own subresource | what got built |
| `generation` and `observedGeneration` | the generation on the approved and built records |
| get the object as YAML, then apply it again | take a built record, strip it, submit it as an order |

## What changes

| Surface | Today | After |
|---|---|---|
| the merged instance schema (since renamed to `registry/entity-view.schema.json`) | one schema, four states folded in | four record schemas sharing one wrapper; the folded shape kept only as a named read-model schema, or removed |
| `registry/examples/` | 12 examples in the folded shape | each becomes an order record and a built record, or is trimmed to the one state it demonstrates |
| `registry/tools/validate.py` and four checks (`check_grant_derivation`, `check_group_invariants`, `check_offer_collapse`, `check_sovereignty_zones`) | read the built state out of one document | read the built record, or the assembled view |
| 16 spec, flow and guide documents that name the schema | describe the folded record | describe the four records; `four-states.md` needs the least change because it already says this |
| the DCM control plane | reads and writes the folded record | writes one record per state change; reads by entity and state |

## What does not change

The entity ID and every relationship that points at it. The four stores and their contracts.
The tamper-evidence chain, which already works per version and now works per record. The audit
store. Who-set-what provenance, which simply splits along author lines. The class model and
everything in the class-tier series.

## Decisions for review

- **D1 — how a record gets its ID.** A time-ordered UUID (version 7) for the record, with the
  entity keeping its stable version-4 UUID. The data model already reserves version 7 for
  time-ordered identifiers.
- **D2 — the combined view.** Keep the current schema, renamed to say it is a read-only view
  assembled from the stores, or drop it and let readers compose their own. I lean keep-and-rename:
  people and dashboards will ask for it, and a schema for a query result is still useful.
- **D3 — how to record the decision.** The spec already decided this and the schema is a defect
  against it. A register row and a schema change, not a new decision record.
- **D4 — when it lands.** The DCM control plane writes this record, so the change spans both
  repos. It lands after the class-tier series, not interleaved with it.
- **D5 — the referee rules.** Drop the `ownership` block. One author per record leaves it no job.
  If a case ever appears where two providers legitimately write one built record, that is a
  finding to investigate, not a reason to keep the field.

## Out of scope

The class model and the Base and Type definitions. The stores' contracts. Retention windows on
the observed stream. How DCM implements the write paths.

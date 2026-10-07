# UDLM in one example

**What this is.** A first read for anyone new to UDLM: one virtual machine followed from the request
that asked for it to the record discovery made of it. About ten minutes. Each step names the file to
open and the document that owns the rule, so you can go deeper wherever you need to.

The example is `app-01`, a VM on a KVM host. Its four records live in `registry/examples/`; CI
validates and seals them on every change, so what you read here is what the gates accept.

## 1. The class says what a VM is

Open `registry/classes/resource/compute/machine/vm.yaml`.

A **class** is a named data contract. `Machine.VM` is a Type of the `Machine` Base: `Machine` holds what
every machine shares (cpu, memory, storage, guest OS), and `Machine.VM` adds what only a VM has
(firmware, networks, placement, a disk layout). Where an element sits is how portable it is: an order
placed at `Machine` can be filled by a VM, a bare-metal host or an LPAR; an order at `Machine.VM` by
any hypervisor. A provider that needs data of its own adds a third tier, a Provider Class.

Classes are filed under usage groups (`compute`) for people to find them; a group is never part of a
name. Owner: `docs/spec/foundations/class-tiers.md`.

## 2. Four records, one per state

An entity is never one document. Each state is its own record, written once by one party and never
edited. All four share `entity_uuid: 2f7c9a41-…` and each has its own `record_uuid`.

| State | Written by | File | What it answers |
|---|---|---|---|
| **Intent** | the consumer | `example-vm-app01-intent-record.yaml` | what was asked for |
| **Requested** | the control plane | `example-vm-app01-requested-record.yaml` | what was sent to a provider, after layers and policy |
| **Realized** | the provider | `example-vm-app01-realized-record.yaml` | what was built |
| **Discovered** | discovery | `example-vm-app01-discovered-record.yaml` | what is actually there |

A change to a published record is a new record that names the one it replaces in `supersedes`.
Owner: `docs/spec/foundations/four-states.md`.

## 3. Intent: what the consumer asked for

The intent asks for 4 CPUs, 16Gi of memory, a guest OS, UEFI with Secure Boot, one network interface
on a VLAN, and a disk layout. Every value it sets has a **provenance** entry naming who set it, here an
actor, `lab/users/app-team-lead`. Nothing in it names a provider.

## 4. Requested: what the control plane decided

Compare it with the intent. Three things were added, and each is accounted for:

- **Fields filled in.** `cpu.sockets` and `cpu.cores_per_socket` came from a CPU-topology policy;
  `placement.location_ref` from a tenant layer; `firmware.vtpm` from a firmware baseline. Each has a
  provenance entry, and `assembly.applied` lists the layers and policies that ran, in order. A
  difference from the intent with no provenance entry fails CI (`TRN-001`).
- **The policies that decided.** `policies` records each one with its decision and the fields it
  touched.
- **What crossed to the provider.** `dispatch` is the receipt: the provider chosen and every field path
  it was given. Dispatch is zero trust: a provider gets the elements of the class it binds and nothing
  else unless a policy grants it (`DSP-001`–`DSP-004`, `docs/spec/contracts/data-roles.md`).

The record points back at the intent with `intent_ref` and the intent's integrity head, so the link
cannot be rewritten without breaking the seal. It also names its `root_request_uuid`, the order it
belongs to.

## 5. Realized: what the provider built

The provider, `lab/providers/libvirt-host-a`, reports the same fields plus **outputs** — the facts that
exist only once something is built: IP and MAC addresses, hostname, the provider's own handle, the
observed run state. Every output has a provenance entry naming the provider. **Dependencies** record
the edges that now exist: contained by host-a, depending on its root volume.

The realized record carries an **integrity** block. The head is a sha256 over the canonical form of the
record and the head of the record it superseded, so each state's history is a chain any reader can
verify. Owner: `docs/spec/contracts/audit-provenance-observability.md`.

## 6. Discovered: what is actually there

Fourteen minutes later a discovery sweep found the VM. It says what it observed and how it matched it
(`correlation_ids`, `matched_by`: the libvirt domain UUID). Its edges are keyed by what discovery could
see, a SMBIOS UUID or a provider id, and resolved to entities when the key matches one.

When discovered and realized disagree, that difference is **drift**, and it is computed, never stored.

## 7. One view of all four

Readers usually want the entity, not four records. The **entity view** folds the latest record of each
state into one read model. It is computed and never written back.

```bash
python3 -c "
import sys, json; sys.path.insert(0, 'registry/tools'); import entity_view as ev
v = ev.load_views(['registry/examples'])['2f7c9a41-8e3d-4b6a-9c15-7d2e4f8a1b03']
print(json.dumps(v, indent=2, default=str))"
```

Owner: `registry/ENTITY-VIEW.md`.

## 8. Check it yourself

```bash
python3 registry/tools/validate.py        # every record and class against its schema
python3 tests/check_integrity_chain.py    # every sealed chain verifies
bash scripts/signoff.sh                   # every gate CI runs
```

## Where to go next

| You want to | Read |
|---|---|
| Understand the class system and portability | `docs/spec/foundations/class-tiers.md` |
| Understand the records and their states | `docs/spec/foundations/four-states.md`, `registry/state-record.schema.json` |
| Reference anything by name or filter by field | `docs/spec/contracts/identifier-scheme.md` §9 (URF) |
| Build a provider for `Machine.VM` | `docs/guides/implementing-a-resource-type.md` |
| Build a system that reads the model | `docs/guides/consuming.md` |
| Author a class, policy or example | `docs/authoring/README.md` |
| Know why something is the way it is | `docs/adr/README.md`, one row per decision |
| Look up a term | `GLOSSARY.md` |

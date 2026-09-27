# UDLM ADR-067: A UPS is a base class of its own — the migration test decides where a type is homed

**Status:** Proposed — decided 2026-09-27, not yet built
**Realized by:** _not yet_ — decided, no machine surface.
**Date:** 2026-09-27
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)

**Background — read first (the cold reader's on-ramp; skip if you have the context).**
`ADR-038 — scope is portability: an element ports across exactly the classes beneath the scope it is declared at`.
`ADR-061 — the classes directory is a verified projection of the class hierarchy; a base is a directory holding _base.yaml`.
`ADR-069 — Facility is a folder, not a deliverable: a location and a power feed are different orders, so Facility is instantiable: false`.
`registry/naming-conventions.md §1 — cross-cutting Resource types are single-segment (Topology); §2 — a new category needs no reasonable existing home and an industry model to adopt`.

---

## Context

The estate needs the UPS behind a power feed to be an entity: its identity, rating, battery age, the
point at which it must raise low-battery, and the telemetry it reports. `Facility.PowerFeed` carries
`feed_type: ups` and NUT-mapped outputs, but the unit itself has no record, so a feed's battery
numbers have no producer to attach to and a battery replacement has nowhere to be recorded
(`docs/research/platform-fidelity-program.md` §3 asks this question).

The first draft put it at `Facility.UPS`. That fails the reason a base exists. `Facility` is a folder
with no elements (ADR-069), so a type beneath it inherits nothing and shares nothing: `Facility.UPS`
and `Facility.PowerFeed` would be siblings in name only. A wider `Power` base was considered next —
Redfish `PowerEquipment` groups UPSes with PDUs and transfer switches, and NUT's `device.type` does the
same — but it fails the same test from the other side.

## Decision

**`UPS` is a base class of its own** (`registry/classes/resource/ups/_base.yaml`, single-segment,
Resource family, instantiable), with the vendor-neutral UPS elements at `UPS` scope and the telemetry
producer as a provider on the instance.

**The test that homes a type:** a base is an order that its members can substitute for one another —
something you could *migrate* between. A workload moves VM → bare metal → LPAR, so `Machine` is a base.
A load moves from a line-interactive UPS to a double-conversion one, so the kinds of UPS (IEC 62040-3
topologies) are members of `UPS`. Nothing ever migrates from a UPS to a transfer switch or a PDU, so
`Power` would be a folder, and folders grant no portability. A location and a feed are not migratable
either, which is what already made `Facility` a folder.

`Facility.PowerFeed` gains `supplied_by → UPS` (0..1) at 0.6.0; hosts keep depending on the feed, so
shutdown ordering is untouched.

## Alternatives considered

- **`Facility.UPS`** — a type under a folder base: no inherited elements, no shared order with
  `PowerFeed`; the name suggests a family that does not exist. Rejected.
- **`Power` base with `Power.UPS`, `Power.PDU`, `Power.TransferSwitch`** — real industry grouping
  (Redfish PowerEquipment, NUT device.type), but its members are not substitutable; the shared
  elements (status, load, voltage) are the *provider's* variable namespace, not a deliverable's.
  Rejected; if a PDU or transfer switch ever needs a class it is its own base.
- **NUT as a `Facility.PowerFeed.NUT` provider class** — models the producer, not the unit; the
  battery and its age still have no home. Rejected.

## Consequences

Easier: a UPS is addressable (identity, battery age, low-battery policy), telemetry has a producer,
`feed_type: ups` becomes a graph edge. A second UPS kind is a member, not a new type.
Harder: `Facility.PowerFeed` is now the one Facility type whose sibling was moved out; by this ADR's
own test a feed is its own order too, so **`Facility.PowerFeed` → a `PowerFeed` base is the recorded
follow-up**, not done here (a rename is a version event across every estate that pins it).
`Facility` then holds only `Location` — a folder with one entry — which is a question for the
class-tier program.

## Data · Policy · Provider

**Data:** the `UPS` class (elements + outputs) and the `supplied_by` edge on `PowerFeed`.
**Policy:** `low_battery_policy` is intent; where the unit's threshold is not writable the realized
value stands and the difference is drift, never a silent overwrite.
**Provider:** NUT, a vendor SNMP card, or a Redfish power shelf realizes the outputs and pushes the
thresholds it can; named on the instance, referenced in `adopts[]`, never in the type.

**Peer test (ADR-008):** a conformant peer must home a UPS as its own base — the elements and the
edge are the substrate; how a peer's provider reads the unit (USB, SNMP, Redfish) is implementation.

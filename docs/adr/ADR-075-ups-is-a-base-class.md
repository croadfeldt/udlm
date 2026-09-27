# UDLM ADR-075: A UPS is a base class of its own — homed by the base test (CLS-002)

**Status:** Accepted (croadfeldt upstream) — requires engineering ratification; maintainer decision 2026-09-27
**Realized by:** `registry/classes/resource/ups/_base.yaml` · `registry/classes/resource/facility/power-feed.yaml` (`supplied_by`) · `registry/generated/ups.json`
**Date:** 2026-09-27
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)

**Background — read first (the cold reader's on-ramp; skip if you have the context).**
`ADR-038 — scope is portability: an element ports across exactly the classes beneath the scope it is declared at`.
`ADR-061 — the classes directory is a verified projection of the class hierarchy; a base is a directory holding _base.yaml`.
`register row 069 / CLS-002 — the base test: (a) an existing, widely used API already abstracts over the members, (b) every base element is honorable by every descendant, (c) an offering at any tier accepts orders at every tier above; nothing moves — the portability events are placement, rebuild and substitution`. `Facility was marked a folder under that test (commit 7238977, CLS-003): no API abstracts a location together with a power feed`.
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

It is homed by the base test of register row 069 (CLS-002), and passes all three conditions:

- **(a) an existing, widely used API abstracts over the members.** NUT's `ups.*` / `battery.*` /
  `input.*` / `output.*` variable namespace and Redfish `PowerEquipment` / `PowerSupply` each address
  every UPS topology — double-conversion, line-interactive, standby (IEC 62040-3) — through one
  interface.
- **(b) every base element is honorable by every descendant.** Identity, rated capacity, battery,
  low-battery policy, outlets and management surfaces are declared and honored by a
  double-conversion, line-interactive or standby unit alike; topology is an element, not a Type
  axis, because it does not change the definition structure (CLS-004).
- **(c) an offering at any tier accepts orders at every tier above.** An order placed at `UPS`
  ("a unit of this rating with this low-battery policy") is fillable by any of them; a load can be
  placed on, rebuilt onto, or substituted between them, which is the illustration, not the test.

The same test explains the two rejected homes. `Facility` fails (a): no API abstracts a location
together with a power feed, which is why it is a folder (CLS-003). A `Power` base fails (a) too:
Redfish `PowerEquipment` and NUT `device.type` enumerate a UPS beside a PDU and a transfer switch, but
no API takes an order for "power equipment" that either can fill — they are catalogued together,
not abstracted over as one deliverable.

`Facility.PowerFeed` gains `supplied_by → UPS` (0..1) at 0.6.0; hosts keep depending on the feed, so
shutdown ordering is untouched.

## Alternatives considered

- **`Facility.UPS`** — a type under a folder base: `Facility` fails CLS-002 (a), so a type beneath
  it inherits nothing and shares nothing with `PowerFeed`; the name suggests a family that does
  not exist. Rejected.
- **`Power` base with `Power.UPS`, `Power.PDU`, `Power.TransferSwitch`** — a real industry grouping
  (Redfish PowerEquipment, NUT device.type) but a catalogue, not an abstraction: no API fills an
  order for "power equipment" with either a UPS or a PDU, so it fails CLS-002 (a) and would be a
  second folder. Rejected; if a PDU or transfer switch ever needs a class it is its own base.
- **NUT as a `Facility.PowerFeed.NUT` provider class** — models the producer, not the unit; the
  battery and its age still have no home. Rejected.

## Consequences

Easier: a UPS is addressable (identity, battery age, low-battery policy), telemetry has a producer,
`feed_type: ups` becomes a graph edge. A second UPS kind is a member, not a new type.
Harder: `Facility.PowerFeed` is now the one Facility type whose sibling was moved out; under CLS-002
a feed is its own deliverable too (Redfish `Circuit` abstracts over utility, UPS, PDU and generator
feeds), so **`Facility.PowerFeed` → a `PowerFeed` base is the recorded follow-up**, not done here (a
rename is a version event across every estate that pins it).
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

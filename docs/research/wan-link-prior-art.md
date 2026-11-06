# What a WAN link looks like: prior art

**What this settles:** nothing yet. It is the research behind a ruling. The estate holds two devices no
class describes, a cable modem and a 5G modem on the home controller (row 164 left them out). This
note reads how six bodies of prior art model the link between a site and a carrier, and ends with the
shape they agree on and three ways UDLM could adopt it. Chris rules; the class follows the ruling.

## The thing to model

The home gateway has two ways out. A DOCSIS cable modem, `Cable Internet`, sits at 192.168.100.1 and
hands the gateway a public address. A 5G unit, `U5G Max Outdoor`, is the second path. The carrier owns
the circuit; Chris owns the modem; the gateway's `wan` segment rides on whichever is up. None of
NetworkSwitch, WirelessAccessPoint or NetworkGateway says what that is.

## Prior art, body by body

**IETF, attachment circuits (RFC 9833 and RFC 9834, 2025).** The freshest and closest match. A
*bearer* is, in the RFC's words, "a physical or logical link that connects a customer node (or site)
to a provider network". An *attachment circuit* is "the required setup to allow successful data
exchange over these links", in the same words. One bearer can carry several attachment circuits. A bearer has a type (Ethernet,
wireless, LAG), a provider-assigned `bearer-reference`, a customer point that names a device or a
site, a provider location, an admin and an operational status with timestamps, and requested and
actual start and stop times. The two-layer split, link below and service above, is the whole lesson.

**IETF, L3 VPN service and network models (RFC 8299, RFC 9182).** The older form of the same split. A
site's `site-network-access` names a *bearer*, and the network model keeps a `bearer-reference` so
the customer view and the operator view stay linked. The bearer is the physical access; the VPN access
is what is provisioned on it.

**IETF, network topology (RFC 8345).** A link is a first-class node of the topology with two
termination points. UDLM already grounds `NetworkSwitch` and `connects_to` on it. A WAN link is one
more link whose far termination point is in a network the estate does not see.

**IETF, network inventory (draft-ietf-ivy-network-inventory-yang, approved, revision pending).** A
network-wide inventory of elements and their components, built on the IANA hardware types (chassis,
module, port). It says what a modem *is* as hardware; it does not say what a circuit is.

**MEF 10.4 and MEF 26.2 (carrier Ethernet).** The *UNI* is the demarcation between subscriber and
service provider; a *UNI access link* is one physical connection that is part of a UNI; the *EVC* is
the service across UNIs; the *ENNI* is the boundary between two operators. Again: a physical access
link, and a service over it, with the demarcation point named.

**TM Forum SID (GB922).** Every resource has a physical aspect and a logical aspect, modeled as two
classes, with the physical hosting the logical. A physical connection terminates on a physical port
of a device such as a cable modem; the port hosts the logical interface. TMF639 inventories all of it.
The same two layers, with the extra point that the modem's port is where the two meet.

**Broadband Forum TR-181 Device:2 (the CPE's own view).** The data model every managed home gateway
and modem speaks (TR-069, USP). It models the WAN side as stacked interfaces: `Device.DOCSIS` (added
in 2.15), `Device.Cellular` (with 5G), `Device.DSL`, joined to IP interfaces by `LowerLayers`. This is
where the discoverable facts of a modem live: technology, link state, firmware, signal. It is the
right source for a discovered record, not a shape for the estate's own class.

**NetBox (the practitioner's inventory).** The de facto model operators keep by hand. A *circuit*
belongs to a *provider*, has a provider-unique *circuit ID*, a user-defined *type* (internet access,
MPLS), a *status* (planned, provisioning, active, offline, deprovisioning, decommissioned), install
and termination dates, and a *commit rate* in kbit/s. It has up to two *terminations*, each at a
site or at a *provider network* (a cloud whose inside is not the user's business), each with a port
speed and an optional upstream speed. NetBox models only physical circuits with two ends.

## What they agree on

- **Two layers.** The physical bearer (RFC 9834 bearer, MEF access link, NetBox circuit, SID physical
  resource) and the service over it (attachment circuit, EVC, VPN access, SID logical resource).
  The estate needs the first layer now. The second can come when a carrier service is worth recording.
- **The provider owns the identity.** The circuit ID or bearer reference is the carrier's. The estate
  records it; it does not mint it.
- **Two ends, one of them opaque.** The near end is a site (and a device at it); the far end is a
  provider network the estate cannot see into. NetBox's provider network and RFC 9834's provider
  location are the same idea.
- **Type, rate, status, dates.** Every body carries the bearer technology, a committed or port rate,
  an operational state separate from an administrative one, and when it started and stops.
- **The modem is the customer termination.** RFC 9834's customer point names a device; SID's
  physical connection ends on the modem's port; TR-181 is the modem describing itself. The modem is
  not the link. It is where the link meets the site.

## Three ways to adopt it

**A. One class, `WanLink`, and the modem is its customer termination.** A Resource Base: `carrier`,
`circuit_id`, `bearer_type` (docsis, fiber, cellular, dsl, ethernet, satellite), `committed_rate`
(down and up), `located_in` for the near end, and an `uplink` edge from `NetworkGateway` to it
(0..n, since the home has two). The modem's identity, firmware and link state are outputs of the
link's discovered record: what the carrier's realization looks like at the site. One class, no
device class for a box nobody configures. The 5G unit and the cable modem become two WanLink
entities. This is the RFC 9834 reading.

**B. Two classes, `WanLink` and a `NetworkTerminal` for the modem.** The link as in A; the modem as an
asset with identity, like a switch, with a `terminates` edge to the link. Honest about the hardware
and lets a modem be placed, powered and retired on its own. The cost is a class whose only instances
are two boxes, and a second record to keep in step with the first.

**C. No new class: the modem is a `NetworkInterface` of the gateway with a `wan` role.** Cheapest,
and wrong for the cable modem, which is its own device with its own address, and silent about the
carrier and the circuit. Listed to be rejected.

Recommendation: A. It carries every fact the estate can observe today, it names the carrier and the
circuit, which the gateway's `segments` cannot, and it adds no class for hardware nobody manages. If a
modem ever needs its own lifecycle, B is a refinement of A, not a replacement.

## Sources

- [RFC 9833, A Common YANG Data Model for Attachment Circuits](https://www.rfc-editor.org/rfc/rfc9833.html)
- [RFC 9834, YANG Data Models for Bearers and Attachment Circuits as a Service](https://www.rfc-editor.org/rfc/rfc9834.html)
- [RFC 8299, YANG Data Model for L3VPN Service Delivery](https://www.rfc-editor.org/rfc/rfc8299.html)
- [RFC 9182, A YANG Network Data Model for Layer 3 VPNs](https://www.rfc-editor.org/rfc/rfc9182.html)
- [RFC 8345, A YANG Data Model for Network Topologies](https://www.rfc-editor.org/rfc/rfc8345.html)
- [draft-ietf-ivy-network-inventory-yang, A Base YANG Data Model for Network Inventory](https://datatracker.ietf.org/doc/draft-ietf-ivy-network-inventory-yang/)
- [MEF 10.4, Subscriber Ethernet Service Attributes](https://www.mplify.net/wp-content/uploads/2018/12/MEF-10-4.pdf)
- [MEF 26 overview, External Network to Network Interface](https://www.mplify.net/wp-content/uploads/2010/01/MEF-Presentation-Overview-of-MEF-26.pdf)
- [TM Forum SID, Resource domain: physical and logical resources](https://www.tmforum.org/Browsable_HTML_SID_R20.0/content/_ATU.wIA.x.jE.e.q3.i.cR.uT.d.zD.zQ-content.html)
- [Broadband Forum TR-181 Device:2 data model](https://device-data-model.broadband-forum.org/)
- [NetBox circuits model](https://netboxlabs.com/docs/netbox/models/circuits/circuit/)

# UDLM ADR-023: Host networking as data — adopt NMstate + RFC 8344 for the addressing family

**Status:** Accepted (maintainer decision, 2026-07-15)
**Date:** 2026-07-15
**Type:** Architecture Decision Record (a `DecisionRecord` with architecture scope — `entities/knowledge-family.md` §4.5)
**Related:** `docs/host-network-and-config-model.md` (the ratified mapping this records — the standards survey, the per-type model, and the `vis` worked case); ADR-013 (hardware component scope — the adapter is a kept component); `design-principles/adopted-standards.md` (Tier-2 adopt-by-reference); the affected types `network.ip-address`, `hardware.network-interface`, `network.dhcp-scope`, `network.address-service`, and the new `network.connection-profile`
**Tracking:** the quality-sweep network cluster (R4/R5/R6) — this ADR is the coherent grounding that resolves them together instead of piecemeal.

> This ADR records the **decision + grounding**; the concrete per-type mapping and worked example live in `docs/host-network-and-config-model.md` (single-source, SPEC-DESIGN §33). It ratifies that proposal (previously "not yet an ADR — react before ratifying").

## Context

UDLM models several networking facts — an interface, its IP(s), DHCP reservations, an address service — but each type grounded itself independently (TOSCA on `ip-address`, Kea/RFC 2131 on `dhcp-scope`, no shared addressing shape), so "networking info" was expressed inconsistently and a static reservation had three possible homes. The `host-network-and-config-model.md` survey found that **the open standards converge**: IETF **RFC 8343/8344** (`ietf-interfaces`/`ietf-ip`), **NMstate**, **NetBox**, and Redfish independently land on the same shape — which is the strongest signal to commit before ratifying.

## Decision

**Ground the whole host-addressing family on the RFC 8343/8344 + NMstate convergent form, adopting NMstate by reference (Tier-2) for host network config.** Concretely (detail in the model doc):

1. **Adapter + MAC** → reuse `Hardware.NetworkInterface` (no change); MAC stays an attribute of the adapter (NetBox's separate MACAddress record is the escalation path only if multi-MAC is ever needed).
2. **IP address** → `Network.IPAddress` becomes an RFC 8344/NMstate-shaped record: `address` (CIDR) + `allocation` as the **origin discriminator** (`static | dhcp | link-layer | random`), with an edge to its `Hardware.NetworkInterface`. **A static DHCP reservation is just `allocation: static`** bound to an interface — not a separate type (matches RFC 8344 `origin=static`, NMstate, Redfish `AddressOrigin=Static`).
3. **Host network config** → one net-new type **`Network.ConnectionProfile`**, whose body **conforms to the NMstate interface schema by reference** (`state`, `ipv4`/`ipv6`, `vlan`/`link-aggregation`/`bridge`/`mac-vlan`, `routes`, `dns-resolver`) — a **Tier-2 adopt**: UDLM owns identity + the conformance pointer, NMstate owns the body. It maps 1:1 to OpenShift `NodeNetworkConfigurationPolicy.spec.desiredState`.
4. **DHCP reservations** → a **projection**, not a hand-list: a reservation is derived from every `Network.IPAddress(allocation: static)` bound to an interface (MAC) contained by a host (hostname). `Network.DHCPScope`/`Network.AddressService` are the **server surface** that renders reservations/leases from that set.

## Why

- **Convergence is the strongest adopt signal.** Four independent open standards agreeing on `{address, prefix, origin}` + parent-by-reference means UDLM should adopt the shape, not invent one.
- **NMstate over nmcli.** nmcli is imperative (commands); NMstate is the **declarative desired-state** API over NetworkManager — the right primitive for a declarative data model. It is **Apache-2.0, a Red Hat project** (RHEL `network`-role backend, OpenShift Kubernetes-NMState operator) — the OSS/RH-aligned choice — and net-negative: it supersedes the bespoke `host_macvlan`/`host_network`/`safe_net_change` Ansible vars.
- **Consistency.** One convergent form for every networking fact: the interface (`Hardware.NetworkInterface`), the address (`Network.IPAddress`), the desired config (`Network.ConnectionProfile`), and the DHCP surface — all speak RFC 8344/NMstate, bound by dependency edges.

## Data · Policy · Provider (required lens — SPEC-DESIGN §29)

- **Data (UDLM):** the four record types above; bindings are dependency edges; identity is uuid/handle.
- **Policy (DCM):** which addresses are static vs pool; reservation constraints (never hand out a reserved IP); who may own/allocate an address (tenant).
- **Provider:** Kea (`Network.AddressService`) renders reservations/leases from the Data under Policy; NetworkManager (via Ansible today, Kubernetes-NMState later) realizes `ConnectionProfile` and reports back discovered MAC/address; the DHCP generator is the read-side provider rendering Kea config from the estate.

## Consequences

- The network family is grounded on one convergent standard set — resolves quality-sweep R4 (dhcp/dns server surface over standard records), R5 (parent/VLAN-by-reference is the convergent form), and reframes R6c (`ipam`-as-a-service stays the odd one out → drop; addressing rides RFC 8344/NMstate).
- One net-new type (`Network.ConnectionProfile`); `Network.IPAddress` reshaped additively; `DHCPScope.reservations` becomes a computed projection.
- A Kea-reservation generator (byte-for-byte parity-checked against today's `dhcp_servers.yml` before cutover — it touches live DHCP) is a separate reviewed PR, downstream of this.

## Options considered

- **(A) nmcli / imperative NM config.** Rejected — a data model is declarative; NMstate is NM's declarative desired-state API and maps to OpenShift NNCP.
- **(B) Invent a UDLM host-network vocabulary.** Rejected — four open standards converge on the shape; inventing violates adopt-by-reference (T5) and drifts from NMstate/OCP.
- **(C) A separate MACAddress record + a separate reservation type.** Rejected for now — MAC is one-per-adapter on the fleet and a reservation is `allocation: static`; NetBox's separate MACAddress is the escalation path if multi-MAC arises.
- **(D) [chosen] RFC 8344/NMstate convergent form, NMstate Tier-2 by reference, reservation-as-projection.**

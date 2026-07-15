# Standards Adoption Register

**Document Status:** ✅ Complete — normative (SPEC-DESIGN-REQUIREMENTS hard constraint 31)

Every standard this project **adopts**, absorbs a **pattern** from, **retires**, or deliberately
**rejects** is recorded here: what, why (including alternatives considered), where it is used,
when (git-derived instant — common-elements §8, no fabricated precision), who decided, and the
license verdict. Entries are DecisionRecord-shaped (entities/knowledge-family.md §4.5 — the
ADR/DR concept, itself adopted not invented); statuses reuse the DecisionRecord curation states.

**Enforcement (`ADOPT-001`):** `tests/validate_registry.py` fails any `adopts[].standard` string
(type specs and provider matrices) that no entry here **Covers**. Adding an adoption without
registering the decision does not merge.

**Default decider attribution:** the project maintainer (recorded session rulings), research + drafting
by claude-fable-5 sessions; deviations noted per entry. **Dates** are the first git commit
introducing the adoption (committer clock, NTP-synced workstation, normalized UTC) unless noted.

**Statuses:** `CANONICAL` (adopted, authoritative) · `PATTERN` (mechanism absorbed, vocabulary
not) · `RETIRED` (was adopted, withdrawn) · `REJECTED` (evaluated, not adopted) · `PRIOR-ART`
(informed a decision; no conformance relationship).

---

## Format & foundations

### JSON Schema 2020-12 — CANONICAL
**Covers:** `JSON Schema` · **Body:** JSON Schema org (IETF-draft lineage) · **Since:** 2026-06-17T18:31:11Z
**Where:** the normative model for every type spec, the meta-schemas themselves, instance validation (hard constraint 1).
**Why:** valid-by-construction requires a machine-enforceable schema language with a mature multi-language validator ecosystem. *Alternatives:* OpenAPI Schema (a dialect of this, API-scoped), protobuf (binary-first, poor for hand-authored specs), CUE (stronger but tiny ecosystem — revisit if constraint logic outgrows JSON Schema). **License:** open specification — compatible.
**Caveat learned 2026-07-05:** `format:` is annotation-only in default validators — normative formats MUST be enforced by `pattern` (§8; the bare-date incident).

### Semantic Versioning (MAJOR.MINOR.REVISION) — CANONICAL
**Covers:** `SemVer` · **Since:** 2026-06-17T18:31:11Z · **Where:** `VERSIONING.md`, every type/spec version, E5 pinning.
**Why:** consumers must distinguish breaking/additive/doc changes mechanically. *Alternatives:* CalVer (encodes when, not compatibility — wrong axis for contracts). Refinement: enum addition = MAJOR unless `x-extensible-enum` (registry-specific rule, documented in VERSIONING.md).

### RFC 9562 (UUID) — CANONICAL
**Covers:** `RFC 9562` · **Body:** IETF · **Since:** 2026-07-05T00:41:50Z (ratified; obsoletes the RFC 4122 references used before) · **Where:** `contracts/identifier-scheme.md` §2.1, hard constraint 30, every uuid in types/instances/estate.
**Why:** universal identity needs one closed version policy: **v4** = identity (CSPRNG, no correlatable structure), **v7** = declared time-ordered fields only. *Alternatives within the standard, prohibited:* v1 (MAC + clock leak), v3/v5 (deterministic — collision-by-construction across independent minters), v6/v8 (interop/underspecified). *Alternatives outside:* ULID/KSUID (no IETF standardization, time-leak by default). **License:** IETF Trust — compatible-reference.

### RFC 3339 / ISO 8601 profile (timestamps) — CANONICAL
**Covers:** `RFC 3339` · **Body:** IETF · **Since:** first referenced 2026-05-27T01:33:19Z; ratified normative-with-patterns 2026-07-05 (common-elements §8) · **Where:** every time field in both schemas, estate records, `time_source` discipline.
**Why:** auditable provenance requires unambiguous instants: UTC-normalized (`Z`), seconds minimum, clock attribution (`time_source`), no fabricated precision. RFC 3339 is the interoperable profile of ISO 8601 (bare ISO 8601 permits zone-less/reduced forms — the ambiguity we're eliminating). Regulatory precedent: MiFID II RTS 25 clock-sync discipline. **License:** IETF Trust — compatible-reference.

### RFC 9162 (Certificate Transparency v2 / Merkle logs) — CANONICAL
**Covers:** `RFC 9162` · **Body:** IETF · **Since:** 2026-04-07T18:38:08Z · **Where:** `observability/universal-audit.md` AUD-006 (audit records form a Merkle tree; leaf signatures), `audit.log_head` in the instance schema.
**Why:** tamper-evident audit for fsi/sovereign profiles needs an append-only structure with an established verification model; CT is the deployed-at-scale precedent. *Alternatives:* blockchain (consensus machinery we don't need), plain hash chain (no efficient inclusion proofs). **License:** IETF Trust — compatible-reference.

### ADR / Decision Record format — CANONICAL
**Covers:** `ADR` · **Since:** 2026-06-19 (knowledge-family §4.5, Findings & Resolutions design) · **Where:** `DecisionRecord` Knowledge entity, DCM ADRs, this register's entry shape.
**Why:** the WHY record is an established practice (Nygard ADRs); UDLM adds only envelope (structure, anchoring, provenance, validation) around the prose. "Never edit, supersede" = UDLM immutability + `supersedes`.

## Relationship & graph semantics (common-elements §9)

### OASIS TOSCA (relationship types) — CANONICAL
**Covers:** `OASIS TOSCA` · **Body:** OASIS · **Since:** 2026-07-06T01:05:46Z · **Where:** relation names `connects_to` (ConnectsTo), `attaches_to` (AttachesTo); the four edge `kind`s are retroactively aligned with TOSCA root relationship types (DependsOn/HostedOn/BindsTo); REL-003 is TOSCA's derivation rule; composition/relationship templates (Software.Service).
**Why:** the only standards-body vocabulary designed for infrastructure topology relationships, with an extension model (derive from root types) matching our augment-don't-fork rule. *Alternatives:* IANA link relations (REJECTED below), DMTF CIM associations (authoritative but aging; Redfish is its living profile — PRIOR-ART), invention (rejected on principle). **License:** OASIS — compatible-reference.

### RFC 8288 (Web Linking) — PATTERN
**Covers:** `RFC 8288` · **Body:** IETF · **Since:** 2026-07-06T01:05:46Z · **Where:** §9's mechanism — relation names come from a declared, extensible registry (here: per-type `relationships[].name`).
**Why:** the registered-vocabulary *mechanism* is exactly right; the IANA *vocabulary* is not (see rejection below). Convergent with TOSCA derivation, Backstage relations, and Zanzibar/SpiceDB per-type relation declarations. **License:** IETF Trust — compatible-reference.

### IANA Link Relations vocabulary — REJECTED
**Since (evaluated):** 2026-07-05 · **Why rejected:** the registered relation types (`next`, `canonical`, `item`, …) are web-document semantics; forcing infrastructure relationships into them violates the don't-force rule of the adoption methodology. The mechanism was adopted instead (RFC 8288 PATTERN above). Recorded so nobody re-evaluates it as "the obvious registry."

## Hardware & platform

### DMTF Redfish — CANONICAL
**Covers:** `Redfish` · **Body:** DMTF · **Since:** 2026-06-26T22:30:12Z · **Where:** 8+ Hardware/Compute/Network/Facility types (ComputerSystem, Processor, Memory, Drive, NetworkAdapter, Switch, Circuit); Bios + BiosAttributeRegistry (Hardware.BiosProfile); Manager + ComputerSystem.Reset (Hardware.BMC); PowerSupply (Hardware.PowerSupply); Location/Placement (Facility.Location).
**Why:** the vendor-neutral hardware-as-asset vocabulary, and the one the estate's producers actually speak (Redfish-capable BMCs; used for bare-metal provisioning). *Alternatives:* IPMI (no data model), DMTF CIM (superseded by Redfish for REST-era use — PRIOR-ART). **License:** DMTF — compatible-reference.

### IEEE 802.1AX / 802.1Q / 802.1AB — CANONICAL
**Covers:** `IEEE 802.1AX` `IEEE 802.1Q` `IEEE 802.1AB` · **Body:** IEEE · **Since:** 2026-07-04T19:10:59Z (AX/Q), 2026-07-04T20:12:42Z (AB) · **Where:** NetworkInterface aggregation/bridge vocabulary; LLDP as the Discovered-entry mechanism for switches and `connects_to` adjacency.
**Why:** the canonical definitions of link aggregation, bridging/VLANs, and neighbor discovery — the probes (`/proc/net/bonding`, `lldpcli`) are implementations of these documents. **License:** IEEE — reference-only (vocabulary referenced, text not reproduced).

### IETF YANG models — RFC 8343, RFC 8345 — CANONICAL
**Covers:** `RFC 8343` `RFC 8345` · **Body:** IETF · **Since:** 2026-07-04T19:10:59Z / 2026-07-04T20:12:42Z · **Where:** `lower_layer` + `parent_device` relation names (8343 `lower-layer-if`; parent_device is a declared 1→N refinement), `supporting_node` (8345), topology node/termination-point grounding for Switch, DEP-006's leafref degrade semantics.
**Why:** interface stacking and overlay/underlay topology are *already standardized* by the IETF network-management models; adopting their names makes our records legible to anyone who knows YANG. *Alternatives:* invention (rejected). **License:** IETF Trust — compatible-reference.

### SNIA Swordfish — CANONICAL
**Covers:** `SNIA-Swordfish` · **Body:** SNIA · **Since:** 2026-06-27T00:11:51Z · **Where:** Storage.Cluster (StorageSystem), Hardware.StorageDevice, Storage.Pool (StoragePool alignment).
**Why:** the storage-domain extension of Redfish — same family as our hardware vocabulary. **License:** SNIA — compatible-reference.

### OpenZFS — CANONICAL
**Covers:** `OpenZFS` · **Body:** OpenZFS project · **Since:** 2026-07-13 · **Where:** Storage.Pool (zpool/vdev topology, redundancy), Storage.Dataset (dataset/zvol, mountpoint, hierarchy, properties).
**Why:** the host-local pool/dataset layer between physical drives (Hardware.StorageDevice/Redfish Drive) and cluster-provisioned volumes (Storage.Volume/Swordfish) had no vocabulary; OpenZFS is the one the producers actually speak (`zpool`/`zfs` on the fleet's storage hosts) and the de-facto standard for the pool→vdev→dataset shape. *Alternatives:* model a pool as Storage.Cluster (wrong — "cluster" is multi-node/distributed; a zpool is single-host) and a dataset as Storage.Volume (wrong — a Volume is a cluster-provisioned PVC/CSI claim, not a host-local hierarchy-bearing filesystem); both rejected as semantic overloads. Swordfish StoragePool aligns the capacity/redundancy fields (§storage family). **License:** CDDL-1.0 — compatible-reference (vocabulary referenced, no code).

## Kubernetes / CNCF ecosystem

### Kubernetes vocabularies — CANONICAL
**Covers:** `Kubernetes` `Kubernetes NetworkAttachmentDefinition` `Kubernetes well-known topology labels` `Kubernetes-Gateway-API` · **Body:** CNCF/Kubernetes SIGs · **Since:** 2026-06-27 (Gateway API, topology labels) → 2026-07-05 (NAD 02:10:32Z, batch Job 03:29:34Z) · **Where:** Network.Gateway (Gateway API), Topology (well-known labels), Network.VirtualNetwork (NAD attachment vocabulary), Automation.Job (batch/v1 run-to-completion semantics — `activeDeadlineSeconds` ≈ `max_execution_time`).
**Why:** k8s is both a major producer and consumer in the estate (OCP) and the de-facto vocabulary source for cloud-native concepts; adopting its names keeps the DCM Provider boundary translation-free. Also adopted structurally elsewhere: `managedFields`/server-side apply is the model behind field `ownership` (R4). **License:** Apache-2.0 — compatible-reference.

### Kubernetes ObjectReference / ownerReference (object-reference shape) — PATTERN
**Covers:** `Kubernetes ObjectReference` · **Body:** Kubernetes (CNCF) · **Since:** 2026-07-14 (UDLM ADR-012) · **Where:** the data-reference shape `{ref_uuid, ref_name, reference_data_type}` (`registry/data-reference.schema.json`) — a field points at a governed Reference Data Layer instead of inlining a copy; `check_data_references` (`registry/tools/validate.py`) enforces referential integrity.
**Why:** k8s already solved "how does one object point at another and stay honest": ownerReferences carry `uid` (authoritative) AND `name` (advisory), the GC resolves on `uid`, and a `uid` that resolves to nothing is a *dangling* edge — never a silent rebind onto a same-named record. We adopt exactly that shape (uuid-authoritative, name-advisory) and its deterministic invalid-edge handling (`OwnerRefInvalidNamespace` → our dangling-reference failure). **Pattern, not vocabulary:** the reference *shape* and integrity discipline, not the k8s field names or the multi-doc apply model. Grounded in `docs/research/minimal-custom-surface-and-graph-resilience.md` findings #1/#2. Convergent with our own uuid+handle discipline (`contracts/identifier-scheme.md`). **License:** Apache-2.0 — compatible-reference.

### KubeVirt — CANONICAL
**Covers:** `KubeVirt` · **Body:** CNCF · **Since:** 2026-07-13 · **Where:** Compute.VirtualMachine (VirtualMachine/VirtualMachineInstance — domain cpu/memory, interfaces->networks, volumes, runStrategy/power).
**Why:** the k8s-native VM realization the estate actually runs (OpenShift Virtualization), the parallel to Metal3 for bare metal — Redfish ComputerSystem gives the vendor-neutral system+power shape, KubeVirt the realization vocabulary. *Alternatives:* OpenStack Nova (not the deployment reality), DMTF OVF (VM packaging/portability — PRIOR-ART, reference only). **License:** Apache-2.0 — compatible-reference.

### Metal3 — CANONICAL
**Covers:** `Metal3` · **Since:** 2026-06-26T22:30:12Z · **Where:** Compute.BareMetalHost.
**Why:** k8s-native bare-metal lifecycle vocabulary (BareMetalHost CRD), OpenShift-aligned (deployment reality + OSS/Red Hat preference). *Alternatives:* pure Redfish (asset view only — no provisioning lifecycle), Ironic-standalone (Metal3 wraps it). **License:** Apache-2.0 — compatible-reference.

### Rook — CANONICAL
**Covers:** `Rook` · **Since:** 2026-06-26T22:30:12Z · **Where:** Storage.Cluster (CephCluster CRD as a provider-side vocabulary; the TYPE stays vendor-neutral per Tier-1 — `provider: ceph` is data).
**Why:** our actual Ceph control surface on OCP. **License:** Apache-2.0 — compatible-reference.

### external-dns — CANONICAL
**Covers:** `external-dns` · **Since:** 2026-06-27T00:01:17Z · **Where:** Network.DNSZone (DNSEndpoint).
**Why:** the cloud-native record-declaration shape. **License:** Apache-2.0 — compatible-reference.

## Network & identity services

### ISC Kea + RFC 2131 (DHCP) — CANONICAL
**Covers:** `ISC Kea` `ISC-Kea` `RFC-2131` · **Since:** 2026-06-26T22:30:12Z / 2026-06-27T00:38:59Z · **Where:** Network.AddressService, Network.DHCPScope (subnet4/subnet).
**Why:** RFC 2131 defines the protocol concepts; Kea is the estate's operational DHCP implementation and its config vocabulary names the operational objects. Kea is MPL-2.0 → **reference-only** verdict (vocabulary referenced, no text reproduction); RFC — compatible-reference.

### IETF DNS — RFC 1035 family — CANONICAL
**Covers:** `IETF DNS` `RFC-1035` · **Since:** 2026-06-26T22:30:12Z · **Where:** Network.AddressService, Network.DNSZone.
**Why:** name-resolution vocabulary is IETF's; nothing to decide. **License:** IETF Trust — compatible-reference.

### Kerberos (RFC 4120) + LDAP (RFC 4511) — CANONICAL
**Covers:** `RFC-4120` `RFC-4511` · **Since:** 2026-06-27T00:38:59Z · **Where:** Security.DirectoryService (the FreeIPA grounding: KDC + Directory).
**Why:** directory services are these two protocols; FreeIPA/AD are providers. **License:** IETF Trust — compatible-reference.

### NUT (Network UPS Tools) — CANONICAL
**Covers:** `NUT` · **Since:** 2026-06-26T22:30:12Z · **Where:** Facility.PowerFeed (`ups.status` vocabulary).
**Why:** the estate's actual UPS telemetry producer (NUT upsd/upsmon daemons); its status vocabulary is the de-facto open standard. **License:** GPL — reference-only.

### Ansible — CANONICAL
**Covers:** `Ansible` · **Since (as adoption):** 2026-07-05T03:29:34Z (Automation.Job `process_type: playbook`); referenced in docs since 2026-04-07 · **Why:** playbook is the estate's dominant Process Resource form; the vocabulary names what actually runs. **License:** GPL-3.0 — reference-only.

### libvirt — CANONICAL
**Covers:** `libvirt virtual network` · **Since:** 2026-07-05T02:10:32Z · **Where:** Network.VirtualNetwork (forward-mode vocabulary).
**Why:** the host-bridge attachment producer on all four virt hosts. **License:** LGPL — reference-only.

## Compute — Container

### OCI Image Specification — CANONICAL
**Covers:** `OCI Image Specification` · **Body:** Open Container Initiative · **Since:** 2026-07-11T00:00:00Z · **Where:** `Compute.Container` image reference (`image.reference` + content-addressable digest).
**Why:** the vendor-neutral image-reference + digest vocabulary; adopting it keeps container image identity portable across any OCI runtime. *Alternatives:* Docker legacy image refs (subsumed by OCI). **License:** Apache-2.0 — compatible-reference.

### Open Application Model — CANONICAL
**Covers:** `Open Application Model` · **Body:** OAM (CNCF lineage) · **Since:** 2026-07-11T00:00:00Z · **Where:** `Compute.Container` infra-neutral workload shape (image, resources, env, ports).
**Why:** an infrastructure-neutral component/workload model matching UDLM's portable-intent goal — the shape is provider-agnostic and the provider naturalizes it. *Alternatives:* raw K8s PodSpec (runtime-coupled; used only as the field vocabulary below). **License:** MIT — compatible-reference.

### Kubernetes Container (core/v1) — PATTERN
**Covers:** `Kubernetes Container (core/v1)` · **Body:** Kubernetes (CNCF) · **Since:** 2026-07-11T00:00:00Z · **Where:** `Compute.Container` runtime field vocabulary (command/args, ports, mounts, restart) — naturalized by the provider, not restated in the base.
**Why:** the de-facto runtime container field vocabulary, absorbed as a naming pattern the provider naturalizes — consumers get familiar fields without coupling the base type to K8s. *Alternatives:* per-provider bespoke runtime fields (fragmenting). **License:** CC-BY-4.0 (docs) — reference-only.

## Storage

### SMB / CIFS — CANONICAL
**Covers:** `SMB / CIFS` · **Body:** Microsoft (MS-SMB2 open specification) · **Since:** 2026-07-11T00:00:00Z · **Where:** `Storage.FileShare` share + access vocabulary (share name, exported path, access, read-only).
**Why:** the dominant cross-platform file-share protocol; its share/access vocabulary is what a portable FileShare type must express. *Alternatives:* NFS (modeled alongside via the `protocol` enum). **License:** Microsoft Open Specification Promise — compatible-reference.

## Cost

### FOCUS — CANONICAL (scoped) / RETIRED (as the platform-wide cost model)
**Covers:** `FOCUS` · **Body:** FinOps Foundation · **Since:** 2026-06-18T01:17:10Z · **Where:** cost-field vocabulary on Compute.Cluster + Data.Database and the cost-management provider matrix.
**Why:** billing-data column vocabulary where cost fields exist. The earlier *platform-wide* cost-model adoption was **retired** (2026-06, adopt-by-reference thesis review) — cost is a projection, not a core modeling axis; the scoped field-vocabulary use remains. **License:** FinOps Foundation — compatible-reference.

### OpenCost — CANONICAL
**Covers:** `OpenCost` · **Since:** 2026-06-18T01:34:51Z · **Where:** Compute.Cluster cost fields, cost-sp provider. **Why:** the CNCF in-cluster cost implementation matching FOCUS-shaped output. **License:** Apache-2.0 — compatible-reference.

## Orchestration & transactions

### TCC (Try-Confirm-Cancel) + Two-Phase Commit (X/Open XA, ISO/IEC 10026 OSI-TP) — PATTERN
**Covers:** `TCC` · `2PC` · **Body:** X/Open (XA DTP) · ISO/IEC 10026 (OSI-TP); TCC = established microservices distributed-transaction pattern · **Since:** 2026-07-13 (ADR-011).
**Where:** two-phase realization — `contracts/provider-contract.md` §6a, `foundations/four-states.md` §2.3a, SPEC-DESIGN hard constraint 15.
**Why:** realization spans providers that cannot share a lock, so it needs a reservation-based commit protocol: **Try = `reserve`** (tentative hold, no side effects), **Confirm = `commit`**, **Cancel = `release`**; DCM is the 2PC **coordinator**, providers are **participants** (a provider that cannot hold votes no by failing reserve), and the **commit barrier** is the global commit decision. **Pattern, not vocabulary:** we adopt the try/confirm/cancel + coordinator/barrier shape and map it onto the existing REST dispatch channel — we do **not** absorb XA's C API or WS-AtomicTransaction/WS-BusinessActivity SOAP envelopes (the transport is already defined). *Contrast — SAGA:* commit-then-compensate; reserve-first avoids most compensation (nothing is built before the barrier), so SAGA applies only to a partially-failed *commit* (`COMPENSATE_AND_FAIL`). **License:** open specifications — compatible-reference.

### Lease (timeout-bounded reservation) — RFC 2131 (DHCP) as protocol precedent — PATTERN
**Covers:** `Lease` · **Body:** IETF (RFC 2131); Gray & Cheriton (leases) · **Since:** 2026-07-13 (ADR-011).
**Where:** reservation-hold TTL — `provider-contract.md` §6a (`requested_ttl` / `granted_ttl` / `min_hold_ttl` / `max_hold_ttl`), `reservation.expired` event.
**Why:** a hold must not leak reserved capacity if reconciliation stalls. DHCP is the near-exact precedent — `DHCPOFFER` = reserve, `DHCPREQUEST`/`ACK` = commit, and **lease expiry = implied release** — which is precisely our TTL semantics (expiry auto-drops the hold and emits `reservation.expired` for audit). **License:** IETF Trust — compatible-reference.

## Attestation, accreditation & sovereignty

*Vocabulary + patterns for the accreditation model (`governance/accreditation-and-authorization-matrix.md`, `registry/accreditation.schema.json`) — adopted after the 2026-07-14 sovereignty-enforcement prior-art review (`docs/research/sovereignty-enforcement-prior-art.md`). The taxonomy cross-walk is matrix §3.10.*

### W3C Verifiable Credentials Data Model 2.0 — CANONICAL (vocabulary)
**Covers:** `W3C-VC` · **Body:** W3C · **Since:** 2026-07-14 · **Where:** the accreditation record's `proof` (`type`/`verification_method`/`proof_purpose: assertionMethod`/`proof_value`) and `trust_anchor`; the issuer→holder→subject→verifier spine (accreditor→provider→capability→DCM); `validFrom`/`validUntil` ≈ `issued_at`/`expires_at`; `credentialStatus` ≈ the verification/staleness block.
**Why:** an accreditation *is* a verifiable credential — a signed, independently-verifiable claim by an authority about a subject. Adopting VC's field vocabulary makes our records verifiable by any VC-aware tool and names the parties the way the identity world already does. **Adopt-not-absorb:** we take the data-model vocabulary, not JSON-LD `@context` machinery or a specific proof suite. *Alternatives:* bespoke signature envelope (re-inventing a solved, standardized shape). **License:** W3C Recommendation — compatible-reference.

### IETF RATS Architecture — RFC 9334 — CANONICAL (vocabulary + pattern)
**Covers:** `RFC 9334` · **Body:** IETF · **Since:** 2026-07-14 · **Where:** the **two-gate** trust decision (matrix §3.7) = RATS's two appraisals (Evidence→Attestation-Result, then Result→policy); Attester/Verifier/Relying-Party ≈ provider/DCM-verifier/placement-gate; the **verification summary** (matrix §3.9) = a RATS **Passport-model** Attestation Result carried forward so each hop need not re-run the raw appraisal; Endorsement ≈ `trust_anchor`.
**Why:** RATS is the IETF's model for exactly "verify evidence against policy, emit a portable result." Its **separation of verification (is the evidence authentic?) from appraisal (does it satisfy policy?)** is the precise justification for our two-gate split, and Passport-vs-Background-check names our per-hop re-attestation choice. **Pattern + vocabulary**, not wire formats (no EAT/CoRIM tokens). **License:** IETF Trust — compatible-reference.

### NIST OSCAL / FedRAMP authorization model — PATTERN
**Covers:** `OSCAL` · **Body:** NIST · **Since:** 2026-07-14 · **Where:** conformance-claims → SSP control-implementation self-assertion; accreditation → assessment-result/ATO; the `scope` boundary ≈ OSCAL **authorization-boundary**; delegation (matrix §3.9) ≈ **leveraged-authorization** (inheriting a provider's existing ATO); gap records (matrix §3.5) ≈ **POA&M**.
**Why:** OSCAL is the government-scale precedent for "declared control implementation vs assessed/authorized," and its authorization-boundary + leveraged-authorization concepts are exactly our scope + delegation shapes. **Pattern:** we adopt the conceptual model (declare→assess→authorize, bounded, leverageable), not the OSCAL JSON/XML catalog format. **License:** NIST (public domain) — compatible-reference.

### Gaia-X Trust Framework — PATTERN
**Covers:** `Gaia-X` · **Body:** Gaia-X AISBL · **Since:** 2026-07-14 · **Where:** the **conformance_claims** self-declaration = Gaia-X **self-descriptions** (provider-authored VCs); `trust_anchor` = Gaia-X **Trust Anchors** / GXDCH clearing; the layered strictness in profiles (dev→sovereign) ≈ **Label Levels L1/L2/L3**; the "declaration-and-placement layer, not a byte enforcer" framing is Gaia-X's own posture.
**Why:** Gaia-X is the closest existing system to what this model is — federated, self-described, trust-anchored sovereignty attestation for cloud providers — and validated the architecture (three-party spine, self-description-then-verify, no central byte enforcement). **Pattern:** conceptual alignment; we don't consume the Gaia-X ontology or credential-event service. *Related:* EUCS assurance levels (PRIOR-ART, informed the plane/level axes). **License:** Gaia-X (open) — compatible-reference.

### SLSA + in-toto (per-hop attestation match) — PATTERN
**Covers:** `SLSA` `in-toto` · **Body:** OpenSSF / CNCF · **Since:** 2026-07-14 · **Where:** per-hop re-attestation down the fulfillment graph (ADR-004 §4, matrix §3.3.1) = in-toto's **layout step MATCH** at each link; delegation (matrix §3.9) ≈ SLSA **VSA** (Verification Summary Attestation — "someone I trust already verified this").
**Why:** supply-chain attestation independently arrived at the same rule we need — **trust is re-checked at every hop, never inherited**, and a verifier can emit a summary others rely on. Confirms the propagation design and names the delegation dial. **Pattern:** the match/summary shape, not the predicate formats. **License:** Apache-2.0 — compatible-reference.

### ISO 3166 (jurisdiction hierarchy) — CANONICAL (vocabulary)
**Covers:** `ISO 3166` · **Body:** ISO · **Since:** 2026-07-14 · **Where:** `geographic_scope` / `operating_jurisdictions` (ISO 3166-1 country) and `data_residency_zones` down to ISO 3166-2 subdivisions (US → US-MN); the **residency-subsumes / sovereignty-exact** rule (matrix §3.8) keys off this hierarchy.
**Why:** residency subsumption ("a US accreditation covers US-MN") requires a standard containment hierarchy of jurisdictions; ISO 3166 is it. **License:** ISO (code lists referenced) — compatible-reference.

### eIDAS / trust-service-provider model — PRIOR-ART
**Since (evaluated):** 2026-07-14 · **Where:** informed the `trust_anchor.type: eidas_tsp` option and the qualified-vs-non-qualified distinction behind trust-anchor typing.
**Why:** eIDAS is the EU legal framework for qualified trust services (the TSPs that would issue real sovereignty credentials); referenced as an anchor type, no conformance relationship. Recorded so the `eidas_tsp` anchor option has a provenance. **License:** EU regulation (referenced).

### SPIFFE / SPIRE — PRIOR-ART
**Since (evaluated):** 2026-07-14 · **Where:** informed TODO #25 (JIT credential mechanism — short-lived SVID-like credentials issued at reserve/commit) and the workload-identity framing of credential-reference passing (TODO #24).
**Why:** SPIFFE/SPIRE is the deployed model for short-lived, attested workload identity — the reference design for the JIT-credential follow-on, not yet an adoption. Recorded to anchor #24/#25. **License:** Apache-2.0 (referenced).

## Prior art (informed decisions; no conformance relationship)

**Since (evaluated):** 2026-07-05, relation-vocabulary research (common-elements §9 records the survey):
CNCF **Backstage** catalog relations (paired vocabulary) · **SPDX** (ISO/IEC 5962) + **CycloneDX**
(ECMA-424) relationship/dependency vocabularies (proof the two-tier generic/specific split is
standardizable) · **Google Zanzibar / SpiceDB** per-type declared relations (the model behind Red
Hat **Project Kessel** `relations-api` — the future DCM↔Insights integration surface) ·
**Service Binding for Kubernetes** (CNCF spec, Red Hat-led — grounds `binds_to`/`bound_field`;
candidate for formal adoption when a type first declares a service-binding relationship) · **DMTF
CIM** associations (Redfish's ancestor) · **W3C PROV** (provenance entry shape agrees with its
agent/activity attribution) · Red Hat **OSAC** fulfillment API (verified 2026-07-05: named
`*_ref` fields, no relation vocabulary — UDLM's model is a superset; Provider-boundary mapping is
name↔ref-field) · systemd ordering-vs-dependency split and VMware SRM recovery plans (informed
the Automation.Job process-dependency design).

---

*Adding an adoption? Add the `adopts[]` entry AND a register entry in the same change —
`ADOPT-001` enforces the pairing. Rejecting one? Register the rejection; it's cheaper than the
next person re-running your evaluation.*

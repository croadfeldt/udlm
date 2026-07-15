# DCM — Unified Provider Contract


**Document Status:** ✅ Complete
**Document Type:** Architecture Foundation
**Related Documents:** [Foundational Abstractions](../foundations/foundations.md) | [Policy Contract](policy-contract.md) | [Governance Matrix](../governance/governance-matrix.md) | [Accreditation](../governance/accreditation-and-authorization-matrix.md)

---

> > **Design Priority:** Provider types implement all four design priorities simultaneously. Security properties (mTLS, scoped credentials, sovereignty declarations, accreditation) are present in all provider registrations. The capability extension model (Priority 3) enables new provider types without changing the base contract. See [Design Priorities](../design-principles/design-priorities.md).

## 1. The Unified Provider Contract

Every Provider in DCM — regardless of type — implements a single base contract. What varies between provider types is the **capability extension**: the specific operations exposed, the data that flows in each direction, and the typed schemas for that exchange.

```
┌─────────────────────────────────────────────────────────┐
│                BASE PROVIDER CONTRACT                    │
│                                                          │
│  Registration · Health · Sovereignty · Accreditation    │
│  Governance Matrix · Zero Trust · Lifecycle              │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │           CAPABILITY EXTENSION                   │   │
│  │                                                  │   │
│  │  What operations this provider type exposes.     │   │
│  │  What data flows in which direction.             │   │
│  │  What schemas govern the exchange.               │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

**Adding a new provider type** = implement the base contract + define a capability extension. No changes to the core required.

**Transport.** The contract is **HTTP/REST + JSON** (AEP-conformant). REST is the floor every provider can meet — it keeps the barrier to implementing a provider in any language low and matches the rest of the API surface. The contract is deliberately transport-shaped (operations + typed request/response schemas), so a **gRPC binding can be added post-1.0** if provider demand warrants it; it is not in v1. gRPC is a later projection of the same operations, not a parallel contract.

**The boundary.** Throughout this document "the boundary" is the **trust boundary between DCM and an external provider** — the point where an assembled payload leaves DCM's control (outbound) or a provider result enters it (inbound). The Governance Matrix (§4) is evaluated at *every* crossing of this boundary because that is precisely where data leaves DCM's governance.

---

## 1a. The Base Level of Integration (the floor)

The **base level** is the minimum a provider must implement for **DCM/UDLM to own the lifecycle** of its target resources — basic lifecycle + the required-data functions that enable that ownership. Everything below is MUST; anything richer is a **capability extension** (§8), i.e. a deeper *scale of integration* (DCM ADR-023 §6), opt-in. A provider at the base level MUST **declare** and **provide**:

1. **Target resource types + capability scope** — which resource types it manages (ADR-004; §2). DCM places/matches against this.
2. **Required data** — the input schema it needs to realize/manage each target resource, so DCM can collect intent and own the lifecycle.
3. **Config-projection detail** — enough config schema/detail for the **DCM interface to project a configuration interface to the user across the config lifecycle**, at the provider's supported scale (basic text passthrough → typed; DCM ADR-023 §6). No detail → DCM still projects a basic text passthrough; more detail → a typed interface.
4. **Lifecycle functions** — the **two-phase realize** pair `reserve` / `commit`, plus `converge` / `decommission`: execute the four-state transitions DCM drives (§6, §6a dispatch). Realization is **reserve-then-commit** (ADR-011): `reserve` validates + holds with **no side effects**; `commit` builds the held reservation; nothing is committed until the whole reserved graph validates. All MUST be **idempotent / re-entrant** (ADR-006 convergence) so DCM can re-drive.
5. **Discovered-state reporting** — report realized/discovered state **back, per resource** (denaturalization, DCM ADR-023 §1), with an **identity correlation** (UDLM `uuid` ↔ the provider's native id). *Without this read-back DCM is blind to reality and cannot own the lifecycle* — it is the load-bearing function that closes the loop and feeds drift/convergence/rehydrate.
6. **Audit** — emit audit events for its actions (state transitions, relationship mutations) into the chain (SPEC-DESIGN §18d; §7).
7. **Relationships** — declare and maintain the target resources' relationships: one authoritative direction, targets that resolve, mutations as explicit forward audit events (SPEC-DESIGN §18a–e).
8. **Security, governance, tenancy, RBAC** — each target resource carries its **tenant** and **governance context** and declares its **security posture** (sovereignty, trust; §2/§4/§5, DCM ADR-022). **Authorization is resolved by DCM as the *authoritative lookup*** — "can actor X do action Y on resource Z" — while the **enabling data (identity, group membership, roles) lives in external systems** (IdP / FreeIPA / RBAC) and is **referenced, not stored**. This is the classic **PDP/PIP split**: DCM is the Policy Decision Point (and gates enforcement); external systems are Policy Information Points that *inform* the decision — the same broker stance as DCM ADR-022 (DCM brokers trust, never custodies it). No provider action bypasses this resolution.

The floor is what makes DCM the lifecycle owner and single pane of glass for the resource at all; the scale of *config* integration (3) can be shallow (text) or deep (typed) without changing that.

## 1b. Relationships — authored intent vs provider-reported realized

A resource's relationships arise at two different points in the lifecycle, and the contract must not conflate them. This is the distinction that settles "who defines the relationship — the request or the provider?": **both do, at different times, about different things** (UDLM ADR-009).

1. **Intent relationships — declared on the catalog item.** The catalog item — **defined by the provider** — declares the relationships the service *needs*. Their role is to **inform DCM what must be requested in connection with the catalog item, and why**; DCM then procures the realized resource that satisfies each relationship and hands it back to the provider in support of the original request. They travel on the wire and inform placement, and are drawn from — but not limited to — the example relationships a resource type illustrates. **UDLM does not enforce a closed relationship set on a type** — a type's `relationships[]` are illustrative templates plus, at most, the few marked `enforcement: structural`; a catalog item or provider MAY declare relationships a type never enumerated. The type spec is guidance, not a gate.
2. **Realized relationships — DCM-authored from the provider's report.** When a provider realizes an intent it creates or binds concrete resources the consumer never named by UUID. The provider **MUST report the realized state and the identity correlation** (UDLM `uuid` ↔ provider-native id) for each resource it created/bound, via the discovered-state read-back (§1a.5) and the dependency-introspection endpoint (§8). **DCM authors the Realized relationship** from that correlation and the request it orchestrated (§1b.2) — the provider supplies the correlation, DCM sets the edge. A provider is authoritative for the *resources it created* (their native ids and state), **not** for the Realized graph; relationships a provider *independently observes* are authored into Discovered (§1b.3). This layer builds the operational graph (blast-radius, impact, rehydration).

**One authoritative direction.** Every relationship is recorded **child → parent** — the dependent names its dependency; a parent is never required to know its children. The reverse view is derived, or rebuilt from the audit chain. Every mutation is an explicit forward audit event (§1a.6–7).

**Strength reflects portability.** A realized relationship the provider cannot guarantee across environments (a specific IP, a specific DNS record) is a **`soft`** dependency — it survives rehydration by being *remapped*, not preserved. Only relationships intrinsic to the resource are `hard`.

**A consumer may override a relationship's category** where their intent requires it. DNS, for example, is `soft` by default (any resolvable name will do, remappable on rehydration) — but a consumer who **must** have a specific FQDN raises it to `hard`, so DCM treats that exact name as a firm requirement rather than a remappable one. The override travels with the request; the default lives on the catalog item.

### 1b.1 Accommodating a broker's custom information (ADR-009 §3)

When a provider brokers a dependency it does **not** own (a VM provider needs a `Network.IPAddress` the IP provider owns — `fulfillment: provider`), it conveys the criteria the dependency needs via a constituent `binding` into the target resource. **Most of what a broker conveys is a shared foundational reference, not custom info** — the IP case needs only the **target `Network.VLAN` segment (or `Facility.Location`)** so the IP provider knows *where* to allocate; no NIC, MAC, or switch-port is involved (binding the returned IP to a vNIC is the VM provider's own post-allocation concern). That path needs **no accommodation** — the base type already references the shared segment.

Accommodation is the **rarer** case: a broker must convey **genuinely provider-specific realize-time state the base type does not model** (e.g. a vendor-specific offload or QoS class). A provider that **owns** a resource type therefore **MUST** make that type accommodate such fields in one of two sanctioned ways, and a **brokering** provider **MUST** use whichever the target offers when — and only when — a shared reference does not suffice:

- **(a) Base-type extension surface** — the target type carries an open extension block (a provider-extension layer, `domain: provider`, `layering-and-versioning.md`) into which the broker's fields are written, namespaced to the contributing provider; the base type stays vendor-neutral.
- **(b) Custom resource type layered on the base** — a derived type (`entities/resource-type-hierarchy.md`) that extends the base and adds the broker's fields as first-class.

A type that supports **neither** — where a genuinely-bespoke field is required — is **non-conformant for brokered fulfillment**. *Note:* `Network.IPAddress` is **not** such a case: it needs only the shared segment reference above, so it requires no extension and no derived type. Accommodation applies only where the base type cannot carry provider-specific realize-time state at all. See UDLM ADR-009 for the end-to-end flow.

**Why.** The goal is to let the broker and the owning provider **exchange the full, contextual information the dependency needs** — not to constrain them to a fixed vocabulary. Usually that information is a **shared reference** both sides already understand (a segment, a location), and nothing bespoke crosses the boundary. Where a broker genuinely must convey provider-specific state the base type does not model, a sanctioned extension (a) or custom type (b) carries it faithfully, namespaced and typed, so nothing is dropped or approximated. Agreeing the shape in advance and validating it at admission follows from this, but the aim is the **complete, contextual exchange** itself.

### 1b.2 Who writes the relationship — DCM by default, provider only when required

A relationship *is* data, and DCM — which orchestrated the request and already holds both the parent and child identities — is its authoritative writer. **By default DCM builds the `child → parent` relationship directly into the Requested and Realized objects**: it requested the child in service of the parent, so it records the edge itself. The provider realizes its resource and reports its **realized state + native-id correlation** (§1a.5); DCM correlates and sets the edge. The provider does **not** receive the parent's identity for this — so nothing about the parent crosses the provider boundary at all. This is the most sovereignty-safe posture and the default.

**Hybrid — the provider holds the relationship only when required.** The parent identity reference crosses to the provider only when **(a)** the provider **needs it to realize** correctly (e.g. a storage provider attaching a `Storage.Volume` to a specific VM must know that VM's reference), or **(b)** a **policy requires** the provider to hold or attest the relationship (a sovereignty/compliance attestation). When it does cross, it is governed:

- **execution slice only** — the parent identity reference (`uuid` + correlation), never the parent's record (ADR-008);
- **sovereignty** — no reference crosses a sovereignty boundary except via the federation/peer path (`data-store-contracts.md` §5); a cross-zone parent is a **cross-zone reference**, not a raw hand-off;
- **tenancy** — the provider MUST be admitted for the parent's tenant/zone (capability admission + Governance-Matrix, PRV-009) before it receives the reference; the reference is tenant-scoped and audited;
- **minimum-necessary** — identity + relationship kind only; the provider is a PIP that *records* the edge, not a custodian of the parent (PDP/PIP + broker-not-custody, DCM ADR-022).

So relationship-writing defaults to DCM (parent data stays inside the control plane), and provider-held relationships are a governed, policy-driven exception — not the norm.

### 1b.3 Authorship and provenance of relationships (by state)

Relationships are authored differently across the four states — where **"authored" means which system *generates the relationship record* in that state's payload**, not who conceived the dependency. Every relationship carries **provenance**, so the graph stays honest across authors:

- **Requested — DCM generates the record.** DCM writes the relationship records into the Requested payload from the assembled, placed request (§1b.2).
- **Realized — DCM generates the record.** DCM writes the relationship records into the Realized payload, correlating the native ids a provider reports (§1a.5) against what it orchestrated. A provider does not generate Realized relationship records; it supplies the correlation, DCM writes the record.
- **Discovered — provider OR DCM generates the record.** A relationship *observed in reality* has its Discovered record generated by whoever observed it — a purpose-built discovery engine, a resource provider's dependency-introspection (§8 / PRV-006), an automation run, or DCM's own probes. There is no single privileged generator of Discovered records; reality flows in from whoever observes it.

**Provenance is captured for every relationship** (the field-level provenance model, §1a / `data-model-core.md`): each edge records its **author** (the provider / discovery-engine / automation / DCM identity), its **state** (requested | realized | discovered), and its **timestamp + mechanism** (authored | discovered | derived | provider-reported | policy-injected). This is what lets multiple authors coexist: where a Discovered edge contradicts a Requested/Realized one, **both are kept**, provenance distinguishes them, and DCM emits a **drift finding** (authored/realized is intent; discovered is reality — `data-store-contracts.md` §2). Provenance also answers "*who* asserted this dependency" for audit and for reconciling a discovery engine against a provider.

## 2. Base Contract — Registration

All providers register through the same pipeline (registration specification is implementation-specific; see DCM repo for the complete flow).

```yaml
provider_base_registration:
  # Standard artifact metadata
  artifact_metadata:
    uuid: <uuid>
    handle: "<tier>/<category>/<name>"    # e.g., "org/compute/eu-west-prod-1"
    version: "1.0.0"
    status: submitted                      # submitted → validating → active
    owned_by: { display_name: "<team>" }

  capabilities: [<verb × domain>, ...]   # the declared capability set (ADR-PROV-002); the accepted
                                         # capabilities/categories are governed by the Capability &
                                         # Category Registry (§9). provider_type, if present, is a
                                         # resolved convenience label derived from this set — never a
                                         # mutually-exclusive type.
  display_name: "<human-readable name>"
  description: "<what this provider does>"

  # All providers declare these. NOTE (DCM ADR-022): the sovereignty_declaration is a CLAIM, not proof.
  # For sovereign/restricted zones DCM honors it for placement only when backed by a resolved
  # sovereign_authorization / adequacy accreditation; an unattested declaration is treated at
  # self_asserted tier (see storage-providers.md §11). Drift detection is the backstop, not the gate.
  # SCOPE (UDLM ADR-004 §4): this is the provider-level DEFAULT stance. A capability MAY override it per
  # (verb × domain) category — finest-granularity-wins — because residency differs by what is realized
  # (e.g. Compute EU-only, Storage global). Trust requires a 1-1 match between each sovereignty claim and
  # an accreditation attesting EXACTLY its scope; a claim at either scope with no matching accreditation
  # is self_asserted and never honored. Claim and accreditation are reconciled, never assumed to agree.
  sovereignty_declaration:
    operating_jurisdictions: [<country_codes>]   # ISO 3166 — sovereignty regime matched EXACTLY (accreditation-matrix §3.8)
    data_residency_zones: [<zone_ids>]           # ISO 3166 subdivisions — residency SUBSUMES down the hierarchy (US covers US-MN)
    enforcement_plane: both                      # data | control | both — WHICH plane is attested (§3.8). A data-plane
                                                 #   requirement is only satisfied by a data|both attestation; for it DCM conveys
                                                 #   the requirement + execution-slice to the enforcing provider and verifies ITS attestation.
    sub_processors: []                   # third parties with data access

  # Self-declared standards adherence (Gaia-X self-description / OSCAL SSP lineage). Each framework is a
  # CLAIM — self_asserted until an accreditation attests it (same claim→attestation escalation as sovereignty,
  # accreditation-matrix §3.7). Declarable per capability/category too (UDLM ADR-004 §4a).
  conformance_claims:
    - framework: <framework>             # e.g. iso_27001, soc2_type2, gdpr
      # level / statement optional

  accreditations:
    # Reference ONLY. status/expiry are NOT restated here — DCM resolves currency from the registered
    # accreditation record at evaluation time (a provider cannot assert a revoked accreditation is
    # still active). The record is a VERIFIABLE CREDENTIAL: DCM VERIFIES its proof + trust_anchor and
    # currency (gate 1) BEFORE appraising the 1-1 scope match (gate 2) — accreditation-matrix §3.7.
    # `framework` is a readability hint.
    - accreditation_uuid: <uuid>         # reference to registered accreditation
      framework: <framework>

  # Data ROLES this provider accepts across the dispatch boundary (ADR-PROV-001;
  # contracts/data-roles.md). Default [execution] — only execution-role data is naturalized
  # to the provider. A provider MAY opt into non-execution roles (e.g. assembly context).
  # The set actually delivered is the INTERSECTION of this declaration and what the
  # Governance Matrix permits at the DCM→Provider boundary — sovereignty policy can strip a
  # role the provider requested; it can never widen beyond this declaration.
  accepts_roles: [execution]             # e.g. [execution, assembly]

  # Endpoints (which endpoints are required varies by type — see extensions)
  health_endpoint: "https://<provider>/health"

  # Zero trust identity
  certificate:
    pem: <provider-certificate>          # provider's mTLS leaf cert (PEM)
    ca_chain: <ca-chain>                 # issuing chain DCM pins for this provider
    rotation_interval: P90D              # max age before DCM expects a rotated cert;
                                         # a cert older than this is flagged at health check

  # NOTE: trust_posture is NOT submitted here. Trust is never self-declared (DCM ADR-022) — the provider
  # submits attestation EVIDENCE (its certificate, accreditation references) and DCM COMPUTES the
  # posture in the dcm_registration_verdict below. A trust_posture supplied in this block is rejected.

  # Declared network reachability — so onboarding a provider is a DECLARATION, not a
  # manual firewall edit. DCM provisions the egress/ingress policy from this block; an
  # operator never hand-edits per-provider firewall rules (resolves the per-provider
  # firewall concern).
  network_reachability:
    egress:                              # destinations DCM must be allowed to reach
      - host: "<provider-host>"
        port: 443
        protocol: https
    ingress:                             # callbacks the provider makes back to DCM
      - endpoint: lifecycle              # maps to the DCM lifecycle endpoint (§6)
      - endpoint: telemetry              # telemetry delivery (§7)
    provisioned_by: platform             # platform provisions policy from this declaration
```

**DCM-assigned registration verdict.** Produced by DCM *after* attestation verification; **not part of the provider's submission** — the provider cannot set these, and a submitted value is rejected. This is the structural guarantee behind DCM ADR-022 (trust is never self-declared):

```yaml
dcm_registration_verdict:                # DCM-OWNED — references the submission above
  provider_uuid: <uuid>
  trust_posture: verified | vouched | provisional   # COMPUTED by DCM from attestation:
                                         # verified = attestation independently checked;
                                         # vouched  = attested by a trusted third party;
                                         # provisional = provider self-asserted only, capability-gated (weakest)
  effective_accepts_roles: [execution]   # INTERSECTION of the provider's requested accepts_roles and what
                                         # the Governance Matrix permits — DCM-computed, authoritative
  capability_admissions:                 # ADR-PROV-003 — PLATFORM-LEVEL admin disposition of each DECLARED
    - capability: realize_resources/Storage   # capability/category. DEFAULT-DENY: a declared capability is
      disposition: approved              # UNUSABLE until admitted; each starts `pending` at registration.
    - capability: realize_resources/Compute   # disposition: pending | approved | provisional | denied — COARSE,
      disposition: denied                # platform-wide. GRANULAR approval (per tenant/zone/resource/context) is
    - capability: serve_data/Network           # POLICY (Governance Matrix), not here. Domain granularity is inherent:
      disposition: provisional           # a category IS verb×domain (approve /Storage, deny /Compute independently).
  effective_capabilities: [realize_resources/Storage]   # COMPUTED intersecting CEILING (ADR-PROV-003); starts EMPTY:
                                         # declared ∩ admitted ∩ registry-enabled ∩ Governance-Matrix-permitted
                                         # (mirrors effective_accepts_roles). A provider can never exceed this.
                                         # Admission history is IMMUTABLE: every admin change is an explicit forward
                                         # CAPABILITY_ADMIT audit event (actor+reason); current = LIFO-newest.
  attestation:
    verified_at: <timestamp>
    method: <how the submitted evidence was checked>
```

Field notes: `rotation_interval` is the maximum certificate age DCM tolerates before flagging; `trust_posture` and `effective_accepts_roles` live in the **DCM-assigned verdict**, not the provider submission — the provider supplies attestation **evidence** (certificate, accreditation references) and DCM **computes** the verdict; a provider-supplied value is ignored/rejected. `capability_admissions` and `effective_capabilities` (ADR-PROV-003) are likewise verdict-side and admin-owned: a **platform admin** dispositions each *declared* capability/category at **platform level** (`pending | approved | provisional | denied` — coarse; **granular** per-tenant/zone/context approval is **policy**, not here), **default-deny** (unusable until admitted), and `effective_capabilities` is the **computed intersecting ceiling** (declared ∩ admitted ∩ registry-enabled ∩ Governance-Matrix-permitted) — a provider holds no authority from declaring, and can never exceed this set. The disposition is **immutable/append-only**: every change is an explicit forward `CAPABILITY_ADMIT` audit event (actor + reason + resulting disposition), and the current disposition is the LIFO-newest such event — the same durability model as relationship edges (SPEC-DESIGN §18a–e). `network_reachability` is consumed by the platform to provision connectivity so no per-provider manual firewall change is required.

**Registration lifecycle states:**
```
SUBMITTED → VALIDATING → PENDING_APPROVAL → ACTIVE
                       ↘ REJECTED
ACTIVE → SUSPENDED | DEREGISTERING → DEREGISTERED | FORCED_DEREGISTERED
```

---

## 3. Base Contract — Health Check

Every provider implements a health endpoint. DCM calls it on the declared interval.

```
GET {health_endpoint}

Response 200:
{
  "status": "healthy | degraded | unhealthy",
  "version": "<provider version>",
  "capabilities_available": ["<list of currently available capabilities>"],
  "details": { }    # provider-specific; DCM treats as opaque
}
```

**DCM response to health states:**
- `healthy` → normal operations; next poll scheduled
- `degraded` → reduced routing preference; platform admin notified (medium urgency)
- `unhealthy` / no response → after `failure_threshold`: status → DEGRADED; new requests not routed
- After 2× `failure_threshold`: status → UNAVAILABLE; drift detection triggered on all hosted entities

---

## 4. Base Contract — Governance Matrix Enforcement

Every interaction with every provider is evaluated against the Governance Matrix before data crosses the boundary. This is not optional and not configurable per provider — it is a base contract requirement.

```
Outbound interaction (DCM → Provider):
  1. Classify all fields in the payload by data_classification
  2. Resolve provider's active accreditations
  3. Evaluate Governance Matrix: permitted | strip_field | deny | redact
  4. Apply field permissions
  5. Audit record written (regardless of outcome)
  6. If DENY: interaction blocked; entity enters PENDING_REVIEW if appropriate

Inbound interaction (Provider → DCM):
  1. Authenticate provider identity (mTLS)
  2. Verify credential scope matches the operation
  3. Accept payload; apply data_classification tags
  4. Store in appropriate store per data_classification
```

**Provider operations (closed vocabulary).** A provider exposes more than registration; credential scope (`scope.operations`, see [Credentials](../governance/credentials.md) §3) is checked against whichever operation is executing:

| Operation | Direction | Endpoint(s) |
|-----------|-----------|-------------|
| `dispatch` | DCM → provider | `{dispatch_endpoint}` — realize/execute an assembled payload |
| `discover` | DCM → provider | `{discover_endpoint}` — enumerate or query existing state |
| `query` | DCM → provider | `{query_endpoint}`, `{capabilities_endpoint}` — read provider data/options |
| `introspect` | DCM → provider | `{dependency_introspection_endpoint}` — observed dependency edges |
| `lifecycle` | provider → DCM | `{dcm_lifecycle_endpoint}` — report a state change (§6) |
| `telemetry` | provider → DCM | telemetry delivery (§7) |

A credential issued for one operation cannot be used for another; a provider receiving an interaction whose scoped operation does not match the called endpoint MUST reject it (`403`).

---

## 5. Base Contract — Zero Trust

All provider interactions operate under the active zero trust posture. Minimum requirement for all providers at all profiles:

- Mutual TLS authentication on every call (both sides present certificates)
- Scoped, short-lived interaction credentials (not long-lived API keys)
- Every call authenticated; no implicit trust from network position or prior calls
- Certificate rotation on declared interval

**Why short-lived, scoped credentials** (not long-lived API keys): zero-standing-trust. Each dispatch presents a freshly issued credential scoped to that one operation and resource, so a leaked credential expires quickly and every use is attributable and audited. A long-lived shared key is standing liability — broad, slow to rotate, hard to attribute. Issuance and lifecycle of these credentials are specified in [Credentials](../governance/credentials.md) §4.2.

Higher profiles add: certificate pinning, per-message signing, hardware attestation.

---

## 6. Base Contract — Provider Lifecycle Events

Providers must report changes to the **lifecycle state of the realized resources they host** — drift from requested state, degradation, capacity events, or an unsanctioned out-of-band change — via lifecycle events. (This is why the base registration payload carries no `state` field: realized state is reported through this channel after realization, not declared at registration.) This is a base contract obligation — not optional:

```json
POST {dcm_lifecycle_endpoint}
{
  "event_uuid": "<uuid>",
  "event_type": "<event_type>",       // resource.drift_detected | resource.degraded |
                                      // resource.capacity_changed | resource.unsanctioned_change |
                                      // resource.decommissioned | provider.capability_changed |
                                      // reservation.ttl_changed | reservation.expired   (§6a two-phase realization)
  "provider_uuid": "<uuid>",
  "affected_entity_uuids": ["<uuid>"],
  "event_timestamp": "<ISO 8601>",
  "severity": "INFO | WARNING | CRITICAL"
}
```

`event_type` draws from the substrate event vocabulary; the full schema for each type is in the [event catalog](event-catalog.md). DCM reconciles the reported state against the entity's requested state and drives drift/degradation handling from there.

---

## 6a. Base Contract — Two-phase realization (reserve / commit / release)

Realization is **two-phase** (UDLM ADR-011): DCM validates and **reserves** every target across the dependency graph, reconciles the reserved graph to a fixed point, checks it against policy, and only then **commits**. This is what lets `fulfillment: provider` (§1b, ADR-009) compute a dependency's realize-time criteria from the reserved parent's facts **before any resource is built**, and makes abort a hold-drop, not a teardown.

**Every provider that implements `realize_resources` MUST support three dispatch request types** — `reserve`, `commit`, `release` — alongside `converge` / `decommission`. They are **operations on the dispatch channel** (an `operation` discriminator on the dispatch payload, §8.1), a base-floor obligation (§1a item 4), not optional extensions:

| Operation (request type) | Phase | MUST |
|---|---|---|
| **`reserve`** | validate + hold | Validate against capacity/identity/policy; **hold** the result (capacity, identity, an allocatable address); return `reservation_hold_uuid`, the **granted TTL** + absolute `expires_at`, and the **computed realize-time facts** (e.g. the reserved placement's port, the reserved address). **No infrastructure side effects.** Idempotent — re-issuing for the same hold returns the *same* hold (and re-grants its TTL — see renew). |
| **`commit`** | execute | Realize the **held** reservation; write Realized State. Issued by DCM only after the commit barrier. **MUST fail if the hold is expired or released** (signals DCM to re-reserve). Idempotent / re-entrant (ADR-006). |
| **`release`** | abort | Drop the hold; return the reserved capacity/identity. Issued on validation failure or cancellation. Idempotent — releasing an already-released or expired hold is a no-op. |

**Each of `reserve` / `commit` / `release` is a governed boundary crossing — same data scoping as any dispatch.** Every request carries **only the `role: execution` slice** of the Requested snapshot (`contracts/data-roles.md`; `PRV-008`) — `reserve` carries just what the provider needs to validate, hold, and compute criteria; `commit` the same slice to build; non-execution (control-plane) roles never cross. The **Governance Matrix fires at every crossing** (reserve, commit, *and* release), so *what data goes to which provider, for what use* is scoped identically across all three phases — the two-phase split adds request types, **not** new data-exposure paths. (For `fulfillment: provider`, the criteria the parent computes and the reserved facts it returns are execution-role data on the same governed boundary; the parent-identity minimum-necessary rule of §1b.2 still applies.)

**TTL is negotiated, and expiry is an implied release:**
- **The reserve request carries a `requested_ttl`.** The provider **grants** a TTL within the **`min_hold_ttl` / `max_hold_ttl`** range it advertises (§8.1) — it MAY clamp the request to that range — and returns `granted_ttl` + absolute `expires_at`. DCM plans the commit barrier against the **shortest** granted TTL across the reserved graph.
- **TTL expiration IS release — but never silent.** No explicit `release` call is required on expiry: once `expires_at` passes without a commit, the provider **MUST auto-drop the hold** and free the reserved capacity, and a later `commit` against it MUST fail. The provider **MUST also emit a `reservation.expired` lifecycle event** (§6) so DCM **records the expiry for audit and updates the request** — re-reserve or re-plan. A stalled reconciliation is therefore self-healing (abandoned holds evaporate rather than leaking reserved capacity) *and* observable (DCM is never left believing a lapsed hold is still valid).
- **DCM does not trust the provider event for correctness — it has its own backstop.** DCM independently tracks `expires_at` (it holds the reserve grant) and arms a **separate watchdog**, `reservation_reconcile_grace` (`lifecycle/operational-models.md` §2), *after* the hold's expiry. If the provider fails to emit `reservation.expired` within that grace, **DCM emits its own `reservation.expiry_unconfirmed` event** (DCM-authored, for audit) and fires the **`RESERVATION_EXPIRY_UNCONFIRMED` Recovery Policy** — which force-resolves via **`RELEASE_AND_NOTIFY_AFFECTED`**: an **explicit `release` to the delinquent provider and to every affected party** (providers holding dependent reservations in the same reserved graph), plus a provider **non-conformance** flag. A provider that skips its required event does not strand the graph — DCM times it out and explicitly releases all parties by policy.
- **TTL is changeable in both directions.** DCM **renews** a hold by re-issuing `reserve` for the existing `reservation_hold_uuid` with a new `requested_ttl` (idempotent — same hold, re-granted TTL) to keep a valid hold alive while the rest of the graph reconciles. A **provider MAY initiate a TTL change** on a hold it granted — extend it, or **shorten** it because it can no longer hold that long — by emitting a `reservation.ttl_changed` lifecycle event (§6, bounded by its own min/max); DCM reconciles by committing sooner or re-planning. A provider MUST NOT silently outlive or undercut the granted TTL without signaling.

The reservation hold is a **first-class, TTL'd** object recorded in the Requested-state resolution (`reservation_hold_uuid` in `placement.yaml`, `entities/service-dependencies.md` §11), so the full reserved graph is auditable **before** commit. A provider with nothing to hold (a purely idempotent config target) MAY implement `reserve` as **validate-only** — validate + return facts, hold nothing (`hold_supported: false`, §8.1) — and `commit` as its realize; the two-phase contract still holds, the hold is simply empty.

```json
// RESERVE — validate + hold, no side effects; DCM requests a TTL, provider grants within min/max
POST {dispatch_endpoint}  { "operation": "reserve", "request_uuid": "<uuid>",
                            "entity_uuid": "<uuid>", "requested_ttl": "PT10M", "spec": { ... } }
// -> 200 { "reservation_hold_uuid": "<uuid>", "granted_ttl": "PT10M",
//          "expires_at": "2026-07-13T18:22:00Z",
//          "realized_facts": { "bound_port": "<Hardware.NetworkInterface uuid>", ... } }

// RENEW (TTL change) — re-issue reserve for an existing hold with a new requested_ttl (idempotent)
POST {dispatch_endpoint}  { "operation": "reserve", "reservation_hold_uuid": "<uuid>",
                            "requested_ttl": "PT10M" }

// COMMIT — execute the held reservation (only after the barrier); MUST fail if expired/released
POST {dispatch_endpoint}  { "operation": "commit",  "reservation_hold_uuid": "<uuid>" }

// RELEASE — drop the hold (abort). Expiry is an implied release and needs no call.
POST {dispatch_endpoint}  { "operation": "release", "reservation_hold_uuid": "<uuid>" }
```

---


## 7. Base Contract — Observability, Logs & Telemetry

Every provider contract includes observability as a base obligation — metrics,
logs, and telemetry for the resources a provider hosts are part of the
contract, not an optional extension.

**Division of responsibility:** DCM does **not need to be the arbiter of the
telemetry data itself** — it is not required to store, own, or adjudicate
metric/log content. DCM's obligation is to **manage the collection**: for
every appropriate resource it must be able to discover what telemetry a
provider can emit, configure where that telemetry is delivered, verify
collection is active, and record those facts in the audit trail. By default
the data flows to the deployment's observability platform; DCM governs that
the flow exists.

**DCM MAY be the arbiter.** Where no external observability platform exists —
or a packaged ("canned") solution is desired — DCM CAN serve as the
authoritative telemetry/monitoring platform itself, fulfilling the collection
obligation *and* the storage/query/alerting role through a deployable
observability component (**dcm-observability**). Both postures satisfy this
contract; the choice is a deployment decision, not an architectural fork.
The reference implementation of this component is being developed with an
observability stack as its test bed.

**Registration declaration (the telemetry descriptor):** providers declare
their telemetry surface at registration alongside other capabilities. **DCM
discovers what telemetry a provider can emit by reading this descriptor — it
does not probe or guess.** The descriptor is the single source of truth for
which signals exist, in what format, and where DCM configures delivery:

```yaml
telemetry:
  metrics:
    supported: true
    exposition: [prometheus, openmetrics]   # standard formats only
    endpoint: <metrics_endpoint>
  logs:
    supported: true
    transport: [syslog, otlp, http_push]
    endpoint: <log_sink_config_endpoint>     # where DCM configures delivery
  events:
    supported: true                          # lifecycle events (Section 6) are
                                             # the minimum; richer streams declared here
  per_resource_scoping: true                 # signals carry entity UUID/handle labels so
                                             # collection is attributable per resource
  per_tenant_scoping: true                   # signals carry tenant scope (X-DCM-Tenant /
                                             # tenant_uuid label) so collection + the
                                             # dashboards/alerts built on it isolate per tenant
```

**Obligations:**
- Telemetry MUST be attributable to the entities it describes (entity UUID /
  handle labels) so collection can be scoped per resource, per tenant, and
  per policy. Because entities carry their group memberships and ownership in
  their own definitions ([Universal Group Model](../observability/universal-groups.md)),
  this attribution is sufficient to scope dashboards, reporting, alerting —
  and the *management* of those artifacts — to the appropriate business /
  operational groups (DCMGroup) with **no side-channel scoping configuration**
  (capability OBS-008).
- Collection configuration changes (enable, disable, redirect) are mutations —
  they are policy-evaluated and audit-recorded like any other change.
- Providers that cannot emit telemetry for a resource class declare that at
  registration; the substrate records `telemetry_unavailable` for affected
  entities (mirror of the dependency-introspection pattern).

**Integration mechanism:** TBD — the leading candidate is UDLM-modeled export
(telemetry entities + the [event catalog](event-catalog.md) with discoverable
schemas per [schema-sharing](schema-sharing.md)), making the telemetry surface
consumable by any external tool with no per-tool adapters. See the validation
use case `dav/use-cases/observability/udlm-universal-telemetry-export.yaml`
(DCM repo) and the Universal Audit Model for the audit-record component of
this surface.

---


## 8. Capability Extensions — Capabilities and Categories

Each provider shares the base contract (Section 1–7) and adds a typed capability extension declaring what it can do. There is **one axis**: the **capability**, expressed as **(verb × domain)** (ADR-PROV-002; capability-discovery §2). What earlier drafts split into "provider kinds" (interaction shape) versus "yielded capabilities" is unified here — both are capabilities:

- The former **kinds** are capability **verbs**: Service/Resource = `realize_resources`, Information = `serve_data`, Process = `execute_workflows`, Peer DCM = `federate`. (A Composite Service is *not* a kind — it is an ordinary `realize_resources` provider registering a multi-resource definition, §8.3.)
- The former **yields** are simply more capabilities: **authentication** = `authenticate`; **credential issuance**, **notification** (`Notification.*`), **ITSM** (`ITSM.*`), and **telemetry** (§7) are `realize_resources`/`serve_data` scoped to those domains. Any provider that declares the capability exercises it — there is no separate "kind of provider."

A provider declares its capabilities once; the **capability categories** (verb × domain; capability-discovery §2.4) it occupies follow, non-exclusive, and are what policy targets. The convenience-labeled blocks below (`service_provider_capabilities`, `information_provider_capabilities`, …) are per-capability **profile extensions** — shorthand for a capability + its domain; the canonical identity is the declared capability set, not the block name.

### 8.1 `realize_resources` — Service / Resource profile

**What it does:** Realizes infrastructure resources. Receives assembled payloads, provisions the resource, returns realized state. The same provider also **declares** other capabilities by declaring their resource types: credential issuance (`Credential.*` — see [Credentials](../governance/credentials.md)), notification delivery (`Notification.*`), and ITSM integration (`ITSM.*`). These are **capabilities declared on a provider, not separate provider types** — a provider that declares `Credential.*` *is* a credential-issuing provider for those types.

**Additional endpoints:**
```
POST {dispatch_endpoint}                      # receive and execute dispatch payload
POST {cancel_endpoint}                        # receive cancellation request (if supported)
GET  {discover_endpoint}                      # parameterless full enumeration of discovered state
POST {discover_endpoint}                      # filtered/scoped discovery — takes a query body
                                              # (filters, scope, resource-type selectors)
POST {dependency_introspection_endpoint}      # receive entity_uuid; return observed dependency
                                              # edges for that entity (see entities/
                                              # service-dependencies.md §3a)
GET  {capabilities_endpoint}                  # return available options (networks, images, storage classes)
```

**Capability declaration extension:**
```yaml
service_provider_capabilities:
  resource_types:
    - fqn: Compute.VirtualMachine
      spec_version: "2.1.0"
      catalog_item_uuid: <uuid>
  two_phase_realization:                # reserve/commit/release — base MUST for realize_resources (§6a)
    hold_supported: true                # false = validate-only reserve (validates + returns facts, holds nothing)
    min_hold_ttl: PT30S                 # shortest TTL this provider will grant on reserve
    max_hold_ttl: PT30M                 # longest TTL this provider will grant; DCM's requested_ttl is clamped to [min,max]
  cancellation:
    supports_cancellation: true
    cancellation_supported_during: [DISPATCHED, PROVISIONING]
  discovery:
    supports_discovery: true
    discovery_method: api_query | passive_event | hybrid
  dependency_introspection:
    supported: true | false
    # If supported: provider returns the observed dependency edges for any
    # entity it hosts when the substrate calls {dependency_introspection_endpoint}.
    # Observation is post-realization and observational only — it is NOT
    # consulted for orchestration. See entities/service-dependencies.md §3a
    # and policies OBS-001..OBS-005 for the contract.
    methods:
      - api_query             # actively query the underlying platform
      - passive_event         # surface dependencies that emit lifecycle events
      - inferred_from_config  # derived from provider-held configuration
    response_sla: PT30S       # MUST be ≤ discovery endpoint SLA (OBS-004)
    max_edges_per_response: 500
  naturalization:
    target_format: openstack_nova | vmware_vsphere | custom
  # cost_metadata is an UNVERIFIED HINT only. The external cost engine is authoritative for placement
  # scoring and cost attribution (contracts/cost-metering-linkage.md — "the engine computes; it never
  # decides"). A provider's self-declared opex MUST NOT be the authoritative input to placement
  # tie-breaking, or a provider could under-declare to win placement.
  cost_metadata:
    opex_per_unit_per_hour: 0.28          # advisory hint; not authoritative
    currency: USD
```

**Data direction:** DCM sends assembled Requested State → Provider naturalizes → executes → denaturalizes → returns Realized State. Separately, on demand, DCM sends `{entity_uuid}` to `{dependency_introspection_endpoint}` → Provider returns observed dependency edges → DCM records them in the Entity Relationship Graph under `edge_nature: observed`.

---

### 8.1a Resource advertisement — inventory, capacity, eligibility (the placement input)

Placement and consumer-selection only work over **real** resources. A `realize_resources` provider therefore **advertises**, per capability/category it offers, the three things placement decides against. This is how the **foundational (root) resources** consumers select get populated (`docs/foundational-resources.md`): the provider that owns them publishes them; the platform data layer may add more; policy governs eligibility.

```yaml
resource_advertisement:                 # returned from {capabilities_endpoint}, refreshed by lifecycle events
  category: realize_resources/Network    # the capability category this advertises for
  inventory:                             # the resources the provider OFFERS, as referenceable resources
    - resource_ref: net-vlan-20          # identity of an offered foundational resource (Network.VLAN, Facility.Location, Storage.Pool, Compute.BareMetalHost, ...)
      resource_type: Network.VLAN
      selectable: true                   # part of the consumer-selectable set (subject to eligibility)
  capacity:                              # the QUANTITATIVE input placement decides against, per offered resource
    - resource_ref: host-a
      dimensions: { vcpu: {total: 96, free: 40}, memory: {total: "512GB", free: "180GB"}, storage: {total: "10TB", free: "3TB"} }
  eligibility:                           # provider-declared constraints; DCM POLICY resolves the final eligible set
    - resource_ref: net-vlan-20
      zone: dmz
      requires_capability: []            # what a consumer must hold to select this
```

Rules:
- **Availability is provider-authoritative; cost is not.** Unlike `cost_metadata` (an unverified hint — a provider must not be able to under-declare cost to win placement, §8.1), advertised **inventory + capacity** are authoritative for *what exists and how much is free*, but **bounded**: DCM cross-checks against realized state, and over-advertising (claiming free capacity that isn't) is a **drift finding**, not a silent win.
- **Refreshed, not static.** Capacity changes are pushed via the `resource.capacity_changed` lifecycle event (§6), so placement reads current free capacity, not registration-time values.
- **Eligibility is policy, not provider fiat.** The provider *declares* constraints; the **org's policy + Governance-Matrix** resolve which advertised resources a given consumer/zone/tenant may actually select (the "org ratifies" rule). A provider cannot grant itself selection authority by advertising.

**Size-class resolution — `instance_size_catalog` (the abstract↔precise bridge).** When a resource type ships sized-by-class (`instance_size` — ADR-014, `common-elements §2.2`), the class is a *comparable but abstract* vocabulary. To let placement compare an abstract size against a **raw** requirement (or resolve one provider's class against another's), the provider **declares its class → raw mapping** here — the provider is the authority on what *its* `medium` is (ADR-014: the provider owns the concrete mapping):

```yaml
instance_size_catalog:                  # per capability/category; the provider's authoritative size classes
  - class: small    resources: { vcpu: { count: 2 }, memory: { size: 8GB } }
  - class: medium   resources: { vcpu: { count: 4 }, memory: { size: 16GB } }
  - class: large    resources: { vcpu: { count: 8 }, memory: { size: 32GB } }
```

DCM resolves `instance_size` → raw via this catalog, then applies the **same** `capacity-sufficient` test as a raw request (a raw requirement selects the smallest class whose resolved resources satisfy it). Split, per ADR-014: the **class vocabulary + ordering** is UDLM (portable/comparable), the **class→raw mapping** is the provider's (this catalog), the **resolution/comparison** is DCM (placement). It is **declared, not live-queried** — placement scores many providers at once, so a per-request round-trip per provider is prohibitive; a provider with *parametric* classes MAY additionally expose a `resolve(size)` callback, but the declared catalog is the default.

**Abstract-value channels & the realized audit record (the same bridge, generalized).** `instance_size` is one instance of a broader pattern: intent may carry an **abstract value the provider resolves** — a size class, or an engine **`version` channel** like `latest`/`lts` (`Data.Database`, ADR-014). The same three obligations apply to *any* such abstract value:

1. **Declare the resolution.** The provider **declares** how it resolves the abstract value to concrete — for versions, its channel → concrete-version map per engine — so placement can **compare, conform, and validate** an abstract request against a raw/pinned requirement (and against an adjacent provider's channel) *before* it commits. **Declared, not live-queried** — same reason as the size catalog.

   ```yaml
   version_channels:                     # per engine; the provider's authoritative channel resolution
     - engine: postgres   channel: latest   resolves_to: "16.4"   supported: ["14.x","15.x","16.x"]
     - engine: postgres   channel: lts      resolves_to: "15.8"
     - engine: mysql      channel: latest   resolves_to: "8.4.2"
   ```

2. **Resolve at naturalization.** When intent is abstract (or omitted → the provider's default channel), the provider resolves to the concrete value it will actually provision (DCM ADR-023).

3. **Record the concrete on the realized resource — for audit.** The provider **MUST** write the resolved concrete value into realized state (for `Data.Database`, `outputs.applied_version`; §1a.5 read-back). This is the load-bearing half: an abstract request (`latest`) is only auditable if reality records *what `latest` became* (`16.4`) at the moment it was applied. Intent carries the abstract; **realized carries the concrete**; the two together are the audit trail. This obligation holds for every abstract intent value, not just versions.

**Placement (DCM ADR-019) selects from `inventory ∩ capacity-sufficient ∩ policy-eligible`.** A consumer's `*_ref` selection (e.g. `placement.location_ref`, `networks[].network_ref`) MUST resolve to a resource in that eligible set; when `fulfillment: platform` (ADR-009), DCM chooses within it. Consumption debits the selected resource's capacity and any applicable **quota** (the tenant-quota structure — the consumption side, September P7).

**Boundary (ADR-008):** the advertisement *shape* (inventory/capacity/eligibility) is UDLM — a peer must read another provider's advertisement identically or placement disagrees. The placement *algorithm* and how a provider computes free capacity are DCM/provider.

### 8.2 `serve_data` — Information profile

**What it does:** Serves authoritative external data to enrich DCM's understanding of resources and business context.

**Additional endpoints:**
```
POST {query_endpoint}            # receive query; return data in DCM unified format
POST {write_back_endpoint}       # optional; receive DCM updates to push to source system
```

**Capability declaration extension:**
```yaml
information_provider_capabilities:
  data_domains:
    - domain: business_data
      data_types: [business_unit, cost_center, product_owner]
      # authority_level is NOT self-declared (INF-006) — DCM assigns it from the admin-owned authority
      # layer. It decides which source wins data conflicts, so a provider naming its own data "primary"
      # would self-grant precedence over the true system-of-record. A value supplied here is ignored.
  query_capacity:
    max_queries_per_second: 100
  confidence_model:
    data_freshness_sla: PT1H
  write_back_supported: false
```

**Data direction:** DCM sends lookup query → Provider returns data in DCM format → DCM enriches entity fields.

---

### 8.3 Composite Service Definitions

> DCM treats composite payloads (multiple constituent resource types delivered as one catalog item) as Composite Services registered by ordinary Service Providers. There is no separate provider type for composition — a Service Provider that handles a multi-resource catalog item registers a Composite Service definition and fulfills the constituents it owns (those flagged `provided_by: self`). DCM handles expansion, placement of `external` constituents, dependency resolution, binding field injection, sequencing, and compensation. See doc 05 (Resource Type Hierarchy) and doc 30 (Composite Service Composition Model) for the full model.

**What it does:** Delivers a composite payload — multiple constituent resource types with declared dependencies and delivery requirements — as a single catalog item. The registering Service Provider declares a Composite Service definition (constituent resource types, dependencies, and delivery requirements) so DCM can place, sequence, and govern the constituents. For its own resource types (`provided_by: self`), the registering provider executes as a standard Service Provider — one constituent payload in, one realized state out. All orchestration, placement, sequencing, failure handling, and compensation are performed by DCM using the declared dependency graph.

> **Full specification:** See [Composite Service Composition Model](../entities/composite-service-model.md) for the complete contract, four-state model, failure propagation, compensation, and system policies (CMP-001–CMP-008).

**Capability declaration extension (summary — full schema in doc 30):**
```yaml
composite_service_capabilities:
  constituent_provider_types: [service_provider, information_provider]
  composition_model:
    execution: dependency_ordered
    max_concurrent_realizations: 10
    max_constituent_count: 20
    max_nesting_depth: 3
  partial_delivery_supported: true
  compensation_supported: true
  resource_types_composed:
    - fqn: ApplicationStack.WebApp
      version: "2.0.0"
      constituents:
        - resource_type: Compute.VirtualMachine
          required_for_delivery: required
        - resource_type: Network.IPAddress
          required_for_delivery: required
        - resource_type: DNS.Record
          required_for_delivery: partial
      composition_visibility: selective
```

**Composite status determination:**
- `OPERATIONAL` — all required constituents succeeded
- `DEGRADED` — required constituents succeeded; one or more partial constituents failed
- `FAILED` — one or more required constituents failed → compensation executes

**Data direction:** DCM expands the catalog request, applies policies to the assembled composite payload, dispatches each constituent's payload to its resolved provider in dependency order (`self` constituents go to the registering provider, `external` constituents go to placed providers), and aggregates the returned realized states into the Composite Entity's realized state.

---

### 8.4 `authenticate` — Auth capability

**Authentication is a capability, not a separate provider type** (parallel to credential issuance — see [Credentials](../governance/credentials.md) §1). A provider that authenticates actors declares the **auth capability**; DCM consumes it the same way it consumes any other yield. Multiple providers may declare it — tenant routing determines which authenticates a given actor. (DCM is itself a consumer of this capability for its own user auth; it does not have to *be* the authenticator — it brokers/consumes, see DCM `DCM ADR-022`.)

**Additional endpoints (a provider declaring the auth capability exposes):**
```
POST {authenticate_endpoint}     # receive credentials; return auth token + claims
POST {authorize_endpoint}        # receive token + operation; return allow/deny
GET  {identity_endpoint}         # return actor claims for a token
```

**Capability declaration:**
```yaml
auth_capability:                 # declared on any provider; not a provider_type
  authentication_modes: [oidc, ldap, saml, mtls, hardware_token]
  mfa_methods: [totp, push_notification, hardware_token]
  rbac_model: flat | hierarchical | abac
  step_up_supported: true
  token_lifetime:
    default: PT1H
    max: PT8H
  federation_capable: true
  supports_session_revocation: true
```

**Data direction:** Consumer sends credentials → the auth-capable provider validates → returns token + claims → DCM extracts actor identity.

> **Credential capability.** Credential issuance is the sibling capability, declared via `Credential.*` + a `credential_capability` block (assurance + attestation level the realization selects against). Its full contract — issuance, rotation, revocation, declare-and-select, the broker model — lives in [Credentials](../governance/credentials.md). Like auth, it is a declared capability, not a separate provider type; DCM brokers it and never holds the value (CPX-001).

---

### 8.5 `federate` — Peer DCM (Federation)

**What it does:** Another DCM instance participating in federation. Treated as a typed Provider with a federation tunnel as the communication channel.

**Capability declaration extension:**
```yaml
peer_dcm_capabilities:
  dcm_version: "1.0.0"
  tunnel_type: peer | parent_child | hub_spoke
  deployment_accreditations: [<accreditation_uuids>]
  # inbound/outbound_authorization here are a REQUEST/advertisement, NOT authoritative. The
  # authoritative authorization scope for the peer channel lives on the LOCAL side of the federation
  # tunnel wire contract (governance/accreditation-and-authorization-matrix.md) — "what the remote
  # peer may request" is set locally. A peer cannot widen its own grants by declaring them here.
  inbound_authorization:                 # requested (advisory)
    - operation: catalog_query
      resource_types: [Compute.VirtualMachine]
  outbound_authorization:                # requested (advisory)
    - operation: placement_query
      resource_types: [Compute.VirtualMachine]
  data_boundary:
    max_classification: restricted
  # trust_posture is NOT declared here (DCM ADR-022). A federating peer submits attestation EVIDENCE
  # (deployment_accreditations above + its federation certificate); DCM COMPUTES the peer's
  # trust_posture in the dcm_registration_verdict (§2) — a value supplied in this block is rejected.
```

**Data direction:** Bidirectional within declared authorization scope. Federation tunnel with mTLS, certificate pinning, per-message signing.

---

### 8.6 `execute_workflows` — Process profile

**What it does:** Executes ephemeral workflows to completion. Unlike service providers that manage persistent resource lifecycle (create → operate → decommission), process providers execute a job and report a result. No persistent resource is created — the entity type is `process_resource` which reaches a terminal state on completion.

**Use cases:** Software installation, backup execution, compliance scan, data migration, certificate rotation, patch application, report generation.

**Additional endpoints:**
```
POST {execute_endpoint}          # receive job payload; begin execution
GET  {status_endpoint}/{job_id}  # poll execution status
POST {cancel_endpoint}/{job_id}  # cancel running execution (if supported)
```

**Capability declaration extension:**
```yaml
process_provider_capabilities:
  supported_process_types:
    - "Process.SoftwareInstall"
    - "Process.BackupExecution"
    - "Process.ComplianceScan"
    - "Process.DataMigration"
  max_concurrent_executions: 10
  timeout_default: PT30M
  idempotent: true
  cancellation_supported: true
  automation_platform: aap | tekton | argo_workflows | direct_api
```

**Data direction:** DCM sends job payload → Process Provider executes → reports progress via status polling or callback → returns result payload on completion. Result payload follows standard denaturalization — provider-native output translated to DCM unified format.

**Lifecycle:** `PENDING → EXECUTING → COMPLETED | FAILED | CANCELLED`. No ongoing lifecycle management — process resources reach a terminal state and stay there.

---

## 9. Capability & Category Registry

The Capability & Category Registry is the authoritative, governed list of the **capabilities and capability categories** (the provider-capability taxonomy — verb × domain; `registry/instances/provider-capability-taxonomy.yaml`) that a DCM deployment accepts registrations for. It follows the three-tier registry model (Core / Verified Community / Organization). It replaces the old "Provider Type Registry" — there are **no provider types**, only capabilities and the categories they form (ADR-PROV-002).

```yaml
capability_registry_entry:
  capability: realize_resources          # a verb from the closed vocabulary
  domain: Storage                        # a resource-type Category (naming-conventions §2)
  category: realize_resources/Storage    # the (verb × domain) taxonomy term = the capability category
  tier: core
  default_approval_method: reviewed      # auto | reviewed | verified | authorized
  enabled_in_profiles: [minimal, dev, standard, prod, fsi, sovereign]
  capability_extension_schema_ref: <uuid>
```

Profile-governed approval methods override the registry defaults. The complete approval method resolution model is implementation-specific (see DCM repo).

A provider registers with a **capability set** (each `verb × domain`), verified at registration (PRV-003); the registry governs which capabilities/categories are accepted, not a mutually-exclusive "kind." Auth, credential issuance, notification, ITSM, and telemetry are ordinary capabilities (`authenticate`, and `realize_resources`/`serve_data` scoped to those domains) — not separate registry types. There is no `auth_provider` or `credential_provider` type; a `provider_type` label, where it appears, is a **resolved convenience label** derived from the declared capability set, never an accepted mutually-exclusive type.

---

## 10. Related Policies

| Policy | Rule |
|--------|------|
| `PRV-001` | All providers implement the base contract. No provider is exempt from registration, health check, sovereignty declaration, governance matrix enforcement, or zero trust authentication. |
| `PRV-002` | Governance Matrix evaluation occurs before every provider interaction. It is not configurable per provider and cannot be bypassed. |
| `PRV-003` | Provider capability declarations are verified at registration. Capabilities not declared at registration cannot be invoked after activation. |
| `PRV-004` | Peer DCM instances are treated as typed providers. Federation is the Provider abstraction applied across DCM instances — not a separate abstraction. |
| `PRV-005` | Adding a new provider type requires implementing the base contract and defining a capability extension. No changes to DCM core are required. |
| `PRV-006` | Service Providers that declare `dependency_introspection.supported: true` MUST respond to the dependency-introspection endpoint for any entity they host. Returned edges are recorded as observed (not declared) per [Service Dependencies](../entities/service-dependencies.md) §3a and policies OBS-001..OBS-005. Providers that do not declare the capability are exempt; the substrate records `dependency_introspection_unavailable` for affected entities. |
| `PRV-007` | Observability is part of the base contract: providers declare their telemetry surface (metrics, logs, events) at registration using standard exposition formats. DCM MUST be able to manage collection — discover, configure delivery, verify activity, and audit-record — for all appropriate resources; it is not required to arbiter the telemetry data itself, but MAY serve as the authoritative telemetry/monitoring platform (dcm-observability) where none exists or a canned solution is desired. Integration mechanism TBD (leading candidate: UDLM-modeled export). |
| `PRV-008` | Only `role: execution` data crosses the dispatch boundary by default (ADR-PROV-001; [data-roles.md](data-roles.md)). The payload a provider receives is the INTERSECTION of its declared `accepts_roles` and what the Governance Matrix permits at the DCM→Provider boundary. Sovereignty/profile policy may strip a role a provider requested; it can never widen beyond `accepts_roles`. `role: assembly` (and other control-plane roles) MUST NOT be naturalized to a provider that has not opted in, and MUST NOT be copied into `states.realized`. |
| `PRV-009` | **Default-deny (ADR-PROV-003).** By default no use of a provider is allowed: a declared capability/category grants no authority and is UNUSABLE until admitted — `effective_capabilities` starts empty. At registration DCM records each declared capability/category in the DCM-assigned verdict (`capability_admissions`) as `pending` — the platform-admin worklist. A platform admin dispositions each at **platform level** (`approved \| provisional \| denied` — coarse, platform-wide) via the Admin API (mechanism: DCM registration spec §7.4a; RBAC `platform_admin`; approver stringency is **profile-governed** per PROF-010 — "default safe": the security default derives from the platform profile(s) in use, and no profile weakens default-deny). **Granular / conditional approval** (per tenant/zone/resource/context) is **policy** — Governance-Matrix rules — not an admin-disposition field; domain granularity is inherent (a category IS verb×domain). DCM enforces only the **computed intersecting ceiling** `effective_capabilities` = declared ∩ admitted ∩ registry-enabled ∩ Governance-Matrix-permitted (mirrors `PRV-008`/`accepts_roles`); a provider can never invoke outside it. The disposition is admin-set (never self-declared); every admission change is an explicit forward `CAPABILITY_ADMIT` audit event (actor + reason), immutable, reconstructed LIFO. `provisional` = admitted but restricted/shadowed. |
| `PRV-010` | **Resource-type extension (ADR-PROV-004, closes #198).** A provider MAY extend a resource type it realizes by ADDING data elements, but MUST NOT override, shadow, or redefine any base element — the base type-spec is closed (`additionalProperties: false`). It **declares** its extensions at registration (which base type + the added elements and their schema), and at realization writes them ONLY into the realized entity's provider-namespaced `provider_extensions` surface; the validator rejects any extension path colliding with a base spec field. Any extension **degrades portability**: DCM computes `portability_breaking: true`, narrows the classification, records the extension keys + bound provider, and **notifies the consumer** before/at realization (silent non-portability prohibited). A genuinely new type is a Tier-2 `Vendor.Type` fork, not an extension; a recurrence across ≥2 providers promotes to a base MINOR. |

---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*

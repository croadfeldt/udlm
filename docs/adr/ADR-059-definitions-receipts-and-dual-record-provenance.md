# UDLM ADR-059: Definitions and receipts — one artifact family; dual-record provenance on OpenLineage

**Status:** Proposed (croadfeldt upstream) — **requires engineering ratification**; maintainer decisions 2026-08-02/03
**Date:** 2026-08-03
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)

**What this settles:** what is authored, what is derived, and what is recorded. One artifact
family (definitions consumed → receipts recorded, everything else a projection); the receipt
reduced to states + one pin + one chain; and provenance as typed chains plus a sealed ledger,
with every write citing its causal pathway. ADR-060 (findings) consumes this and ratifies
separately.

**Background — read first (the cold reader's on-ramp; skip if you have the context).** Each cited
once with what it settles.

- **ADR-038** (scoped resource-type Classes): Base → Type → Provider Classes composed from
  `SharedDataElement`s; *scope position IS portability* (§3 derives an instance's portability from
  where its populated elements sit); a generator compiles each Type Class to the flat spec
  consumers read. This ADR completes that direction: the flat spec stops being an authored
  artifact at all.
- **ADR-033** (Pattern/Template/System): the template tiers already map to Intent / Requested /
  Realized — the class hierarchy and the request lifecycle are one story, told twice.
- **[`contracts/provider-contract.md`](../../contracts/provider-contract.md) §8.1**: a capability
  declaration names `resource_types[{fqn, spec_version, catalog_item_uuid}]` — the provider →
  capability → catalog-item lineage this ADR makes explicit.
- **[`foundations/four-states.md`](../../foundations/four-states.md)**: Intent is immutable after
  submission; Discovered has a dual role (snapshot stream under the RHY-008 retention ceiling +
  durable inventory, exempt). Both facts are load-bearing below.
- **[`foundations/context-and-purpose.md`](../../foundations/context-and-purpose.md) §4**:
  field-level provenance is a structural requirement — "audit reads lineage recorded at the point
  of change, not reconstructed from logs." Reinterpreted (not weakened) by Decision 4.
- **ADR-051** (identity/version/digest): uuid frozen; (identity, version) immutable once
  published; non-normative surfaces stripped from the identity digest — the strip machinery
  Decision 3 reuses for `integrity`.
- **ADR-054** (references-context): orthogonal data is a classified, dereferenceable edge — never
  copied into the record.
- **DCM ADR-024** (layers stage data; policies refine and validate): the seam Decision 5 keeps.
- **DRV-001 / SPEC-DESIGN-REQUIREMENTS §37** (derivability): values the model computes are not
  stored. Applied here until it deleted this ADR's own first draft of the receipt shape.
- **ENT-006**: the entity uuid is immutable across rehydration, provider migration, ownership
  transfer — what makes a port a version transition, not a new identity.
- **ADR-039** (vocabulary intake ladder): scope promotion is the portability-improvement
  operation — Decision 6's port-mapping census feeds it.
- **Issue #323** (class schema carries elements only): outputs/relationships/adopts/context have
  no class-side home — reframed by this ADR as the first work item of the conversion program.
- **`AUD-002`** ([`observability/audit-provenance-observability.md`](../../observability/audit-provenance-observability.md)):
  tamper-evident audit — the requirement the merkle chains realize.

---

## Context

Three artifact populations grew in parallel — authored flat resource-type specs, class artifacts,
and provider/catalog surfaces — with overlapping content and no single statement of which is
primary. Operating a real estate against the model showed the cost: hand-authored flat specs
maintained like outputs, catalog items with ambiguous parentage, and a provenance design pulled
between in-record history (unbounded growth in the operational store) and external lineage
(availability coupling). This ADR settles the artifact model and the provenance architecture in
one decision set, because they turned out to be the same question: *what is authored, what is
derived, and what is recorded?*

## Decision 1 — One artifact family: definitions consumed, receipts recorded

A **definition** is a scope-tiered Class (Base → Type → Provider) *offered for consumption*. A
**receipt** is a realized entity — *the consumed, instantiated definition*. The difference is
lifecycle state, not kind.

Everything else is a **projection**, computed and never authored:

| surface | is | derived from |
|---|---|---|
| flat resource-type spec | the receipt-validation schema | generator over the definition stack (ADR-038's compiler, made total) |
| catalog | the definitions the organization exposes | definitions + org curation + access policy |
| capability declaration | the provider's published definitions | provider-contract §8.1, unchanged |

**Format follows nature:** authored definitions are YAML; machine surfaces — generated specs,
receipts, wire packets — are JSON. The yaml/json split stops being style and becomes the
authored/derived boundary.

## Decision 2 — The pipeline is a scope descent

Intent arrives at the scope the consumer bound: **Type scope** (portable — placement chooses the
provider branch) or **Provider scope** (the consumer opted into specificity — permitted, priced,
visible; whether it is allowed at all is organizational policy). Placement selects the branch;
policies apply layers; enrichment populates provider-scope elements; the receipt is the flattened
leaf. Portability is therefore derivable at intent time *and* receipt time from where populated
elements sit (ADR-038 §3) — the catalog projection shows the price of specificity before it is
paid.

## Decision 3 — The receipt carries state, a pin, and a chain. Nothing else.

The working record is:

- **`states`** — the four states themselves. Intent, immutable after submission, travels *in* the
  record; this single fact makes the rest of the design derivable.
- **`resource_type` @ pinned spec version** — the one pin (an existing field). It resolves the
  entire ancestor definition stack through the registry; pin-manifest content digests make the
  resolution deterministic at any future time.
- **`integrity`** — the Layer-1 merkle chain over the state timeline (Decision 4).

**The record-content test** (normative, and the rubric for every future "does X belong in the
record" question): *the working record carries what operations need to act now without any other
system; the ledger carries what audit needs to explain the past.*

**Considered and rejected** (each fails the test, or DRV-001, or both): a `composition` block —
the definitions stack is derivable from the leaf pin, and a port never needs the source's layer
list (the target re-runs its own layers and policies; which source layers supplied a value is
explain-past, the ledger's); a pinned `policy_set` — a pin pretends policies are static when
their application is conditional per run, and the applied-policy list *is* lineage; a
`governed_fields` partition map — the partition derives from the states (Decision 7). The
receipt stores nothing about its own assembly.

**Claims discipline:** the working record makes **state claims only**; nothing in it is named
provenance, lineage, or history. The ledger alone makes **history claims** — only sealed,
chained, anchored records may be cited as lineage. Presenting record content under a "lineage"
heading is a defect, in any surface. Verification joins the two families mechanically: every
seal embeds the working copy and its chain head.

## Decision 4 — Provenance chains, typed by what they protect

**Two pathways cause action**, and only these feed the chains: **request** — "I want a
change" (an actor, or an external system acting as one) — and **data** — "I have data,"
either probe-sourced (discovery) or provider-sourced (the out-of-band lifecycle events the
provider contract already obligates). An **inquiry is not a pathway**: a read changes nothing
and is a *consumer* of the audit surface — verification walks, ledger queries, point-in-time
reconstruction are what the chains exist to serve. (Whether reads are access-audited is a
policy question, and an access-audit event is not a chain link.) Chains follow **the thing
whose integrity they protect** — a pathway or a lifecycle:

| chain | protects | lifetime |
|---|---|---|
| **request** | pathway integrity — the request record's journey (intent intake → assembled → policy-approved → dispatched → callback-reconciled); covers the approval→dispatch tamper window | the request; closes at its terminal state |
| **discovery run** | pathway integrity — probe → ingest → apply; the observation unaltered in flight | the run; transient — retention is profile/policy (RHY-008). Successive runs do **not** chain to each other: observations are independent evidence, and cross-time record integrity is the resource chain's job |
| **resource** | lifecycle + audit integrity — the record's version timeline | the resource, permanently. **Any** new version appends, whichever pathway caused it — Discovered stays tamper-evident on the record |
| **audit log** | the history itself | forever, externally anchored |

**The resource chain (in-record).** Each version's `integrity.head` is computed over the
RFC 8785-canonical record minus `integrity.*` (the ADR-051 strip machinery) and links the
previous version's head. DCM is the sole hasher.

**The seal (ledger-side).** Every change seal is an OpenLineage event embedding the working
copy and its resource-chain head (the `udlm_workingCopy` facet — the one-way bridge; the
working record never references the ledger, so operations never hang on compliance storage),
plus:

- `udlm_provenance` — the modification chain: source kinds, previous values, and dual
  attribution (`source` = the applying policy, `via_layer` = the pinned layer that supplied the
  value). The former in-record field-provenance block's content, housed here.
- `udlm_context` — attribution and cause: the IdM principal (resolved at sign-in, carried
  through the pipeline, never re-looked-up at write time), intent reference, change/approval
  references, the policy decisions that permitted the write, `consulted[]` citations —
  `(uuid, version, head)` of any orthogonal record that materially participated in a decision
  (consulted → cited; unconsulted → just an edge) — and **`pathway_ref`**: the citation of the
  causal pathway anchor — `(request_id, request_chain_head)`, `(run_id, discovery_run_head)`,
  or `(provider_id, event_id)` for provider-driven writes (the anchor is the authenticated
  lifecycle-event channel the provider contract already obligates — mTLS + attestation answer
  "is this really the provider"; no chain over the provider's event stream by default, the
  same independence analysis as discovery runs, with the per-profile posture below). The same
  citation mechanism as `consulted[]`, pointed at causation: it makes the provenance of a
  request verifiable **through to end state** — pathway anchor → seal citation → resource
  chain → audit log, one mechanical walk.

**The admission rule — continuity of provenance as a gate, not an aspiration:** a state write
without a citable pathway anchor is **refused**. Every seal names its cause; there are no
anonymous injections, from any source. This single rule is what makes the injection mechanism
**source-blind**: intent-sourced, discovery-sourced, and provider-sourced changes all enter
through the identical contract — sealed event + pathway citation + resource-chain append — and
everything downstream (comparison, findings, audit walks) never needs to know how data arrived,
only that it arrived governed.

The audit log is a **Merkle log (RFC 9162)** — the repo's standing audit ruling; a linear
framing of the log is a defect. UDLM specifies the **log contract only** — append-only,
Merkle-verifiable, root externally anchorable, third-party auditable; the store is an
implementation choice. Corruption isolates per-asset (one resource chain breaks) while the log
stays globally verifiable and locates when the corruption entered.

**Coverage mandate:** provenance covers **all data on all records across the full lifecycle** —
from Intent intake through layer application and policy writes to Realized. No unsealed writes.
Discovered seals are included, with **retention decided by profile/policy** (the snapshot
stream's limited lifecycle rides the existing RHY-008 machinery; the durable-inventory role
keeps its exemption).

**Accepted asymmetry, stated deliberately:** when a discovery-run chain expires under its
retention policy, the `pathway_ref` citation in the seal remains but is no longer independently
walkable — the probe pathway can't be re-verified, while record integrity is unaffected (the
resource chain and the audit log persist). That is the retention trade the policy makes, not a
gap.

**Point-in-time reconstruction is a ledger query** — the embedded snapshot at T, verified
against its resource-chain head — an audit question answered in the audit home.

## Decision 5 — Carriers split by nature

- **Static shared data → authored layers**: versioned, pinned, genuinely reused (org defaults,
  facility/site data — the directly-used sidecar values). Policies decide layer
  *participation*; declared base→request precedence decides merge *order* — assembly is never
  policy-sequence-dependent.
- **Dynamic policy writes → direct writes, sealed per-field**: linear (one seal entry per
  write), with dual attribution where a layer supplied the value. Synthetic per-run "decision
  layers" are rejected: a policy writing five fields under one condition and six under another
  would mint a versioned artifact per outcome — combinatorial artifacts for zero reuse, when
  reuse is the only reason layers exist.
- **Orthogonal sidecar facts → ADR-054 edges**, never embedded (the information-providers
  "copy the data in" anti-pattern). When consulted by a decision, cited in the seal by
  `(uuid, version, l1_head)` — a tamper-evident cross-record join; the cited entity's own dual
  records hold the content.

## Decision 6 — OpenLineage, adopted by reference; its gaps assigned, never patched

The provenance interchange is **OpenLineage** (T5 adoption: identity + version-pinned
conformance + binding; never re-expressed): pipeline stage = Job, request traversal = Run,
record state = Dataset, field provenance = column-lineage facets, the UDLM facets above as
custom facets.

| OL lacks | assigned to |
|---|---|
| tamper evidence | Data — the merkle chains (Decision 4), realizing `AUD-002` |
| completeness + delivery guarantees | Policy + platform — a declared completeness policy; the platform proves emission |
| tenancy + authorization | platform — the ledger store's isolation, never the event schema |
| sovereignty semantics | data itself — residency/classification travel with the record; the Governance Matrix gates emission per facet, tenant, and boundary like any cross-boundary flow |
| identity/attribution (no actor model in OL core) | the `udlm_context` facet, sourced from IdM |

OL-*ingested* lineage (an external platform's events feeding dependency edges) enters as
Discovered, self-asserted tier — an ingestion avenue, never an attested source.

## Decision 7 — Portability is a computation over the states

The tier partition derives; nothing stores it:

1. **Consumer intent** = the Intent state — read, not reconstructed. Replayed on port; uuid
   preserved (ENT-006).
2. **Provider residue** = provider-scope elements, resolved from the definitions the leaf pin
   reaches. Discarded and re-naturalized down the target branch.
3. **Org/site context** = the remainder. Stripped; the target re-runs *its own* layers and
   policies.

A traveling receipt needs no ledger and no assembly metadata — intent travels in the states.

**Port residue resolves per element** against the target class: no equivalent and policy-classed
ignorable → dropped, with the fidelity degradation and authorizing policy sealed (never
silent); no equivalent and not ignorable → the port refuses or routes to review; compatible →
the **compatibility ladder**: *mapped* (a translation policy, `mapped_from` attribution in the
seal) → *shared element* (both provider classes bind the same `SharedDataElement`; the value
carries) → *adopted class* (the target realizes the source's provider class). Mapping seals are
the **scope-promotion backlog**: an element frequently translated between providers is shared
vocabulary asking for ADR-039 promotion — the ledger measures where the hierarchy grows next.

## Findings — split to ADR-060

How detected conditions (drift, tamper, staleness, cadence-miss) are represented — sealed
ledger interpretations with an open/close lifecycle, never record fields — is **ADR-060**,
which consumes this ADR's admission rule and claims discipline and ratifies separately.

## Worked example — the port

`web01`, realized on `Compute.VM.OCPVirt`, ported to `Compute.VM.VMware`:

1. **Rebuild the hierarchy**: the leaf pin resolves Compute@1.0.0 → Compute.VM@1.0.0 →
   Compute.VM.OCPVirt@1.0.0; spec elements partition by declaring scope (cpu/memory/guest_os at
   Base; firmware at Type; namespace/instance_type/run_strategy at Provider).
2. **Extract intent**: the Intent state — `{catalog_item: vm.standard, params: {name: web01,
   size: small, environment: dev}}`. Note `cpu: 2` is *not* intent: the consumer said `small`;
   policy applied a sizing layer. At a target where small means four, the consumer still gets
   what they asked for.
3. **Replay down the VMware branch**: placement selects it from capability declarations;
   policies re-run against the target's layers (`network_zone` re-derives from the target
   facility's layer); enrichment fills VMware-scope elements; reserve → commit → realized.
4. **Both records afterward**: the working record has the same uuid, a new version whose
   `integrity.head` links the pre-port head — one unbroken chain across providers. The
   migration seal carries the principal, the approval, the placement basis, the consulted
   facility citation, the **`pathway_ref`** citing the migration request's own chain head
   (the ask, verifiable through to this end state), the composition swap with previous
   values, and per-element port dispositions (`preference` dropped per the fidelity policy, recorded; `eviction_strategy`
   mapped via `mapped_from`).

## Data · Policy · Provider

- **Data (UDLM):** the artifact family and its two states; the receipt shape (states + pin +
  chain); the record-content test and claims discipline; the ledger *contract*; the OL facet
  schemas; sovereignty as data on the record.
- **Policy (DCM):** placement, layer participation, every policy write (sealed); emission
  completeness and delivery; provider-scope consumption permission; port fidelity classes;
  Discovered-seal retention; Governance-Matrix emission gating; the finding policies (ADR-060) and
  response matrix per finding class; per-profile posture on pathway continuity citations
  (provider event streams and discovery runs).
- **Provider:** publishes definitions (capability → catalog lineage, §8.1 unchanged); realizes
  receipts (writes Realized as a receipt, through DCM's sealing); naturalizes provider-scope
  elements; never hashes and never self-declares trust.

## Consequences

- The in-record field-provenance block (**#191/E4**, `realized-entity.schema.json`) migrates to
  the `udlm_provenance` facet. [`context-and-purpose.md`](../../foundations/context-and-purpose.md)
  §4 is reinterpreted, not weakened: audit records are a UDLM record family, so lineage stays
  *in the model* — housed in the family whose job is history.
- **#323 is the conversion program's first work item**: definitions must carry everything
  (outputs, relationships — declared consumer-side — adopts, context), because nothing else is
  authored anymore.
- Flat specs become generated; catalog items become projections; the authored surface of the
  registry shrinks to definitions, layers, policies, and instances.
- Contracts and mechanisms are realigned to match (sealing joins the provider write contract;
  consumer-api states the per-scope request/receipt surface; the DCM policy-obligations register
  gains the emission, retention, and port-fidelity obligations; operational runbooks gain ledger
  operation and chain verification — the walker treats a record failing L1 verification as
  REFUSING). Tracked as the conversion/cleanup program, one small PR at a time.
- **Future item (separate issue):** a common repository/process for cross-provider type
  adoption — providers adopting other providers' resource/process classes for compatibility and
  migration targets, on the federated-contribution machinery with attestation-gated admission.

*The one-line summary: best data is none or derivable — and the four states already were the
data.*

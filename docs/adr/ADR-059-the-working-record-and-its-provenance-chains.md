# UDLM ADR-059: The working record and its provenance chains

**Status:** Proposed (croadfeldt upstream) — **requires engineering ratification**; maintainer decisions 2026-08-02/03
**Date:** 2026-08-03
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)

**What this settles:** the two truly novel rulings of the definitions-and-receipts cycle — the
**working record's shape** (states + one pin + one chain, nothing else; state claims only) and
the **provenance architecture** (typed chains, sealed writes, the admission rule). Everything
else that cycle decided lives in its home: the artifact-family/projection/portability rulings
in the **ADR-038 addendum**, the OpenLineage disposition in **adopted-standards.md**, the
provenance-home reinterpretation in **context-and-purpose §4.3 / data-model-core E4**. ADR-060 (findings) consumes this ADR and ratifies
separately.

**Background — read first (the cold reader's on-ramp; skip if you have the context).**

- **ADR-038 + its 2026-08-03 addendum**: the Class paradigm, completed — flat specs generated
  (projections of the definition stack), catalog/capability lists as projections, scope
  descent, portability as a computation over the states with the port-residue ladder. This ADR's record shape is what
  makes that addendum executable.
- **[`foundations/four-states.md`](../../foundations/four-states.md)**: Intent is immutable after
  submission; Discovered has a dual role (snapshot stream under the RHY-008 retention ceiling +
  durable inventory, exempt). Both facts are load-bearing below.
- **[`foundations/context-and-purpose.md`](../../foundations/context-and-purpose.md) §4.3**: the
  provenance obligation is reconstructability from stored model facts; its ruled home (this
  cycle) is the audit/OL record family.
- **[`design-principles/adopted-standards.md`](../../design-principles/adopted-standards.md) §7**:
  the OpenLineage adoption disposition (identity + version-pinned conformance + facet binding).
- **ADR-051** (identity/version/digest): non-normative surfaces stripped from the identity
  digest — the strip machinery `integrity` reuses.
- **DRV-001 / SPEC-DESIGN-REQUIREMENTS §37** (derivability): values the model computes are not
  stored. Applied here until it deleted this ADR's own first draft of the receipt shape.
- **ADR-052** (intent fulfillment / convergence): the declared window and derived verdicts the
  seals interact with.
- **`AUD-002` / [D2] ([`foundations/data-model-core.md`](../../foundations/data-model-core.md))**:
  audit integrity is the RFC 9162 Merkle model — the requirement and structure the ledger
  realizes.
- **Issue #191 / E4**: the in-record field-provenance block this ADR supersedes (pending
  execution — see Consequences).

---

## Context

Operating a real estate against the model pulled the provenance design between two bad shapes:
in-record history (unbounded growth in the operational store) and external lineage
(availability coupling — operations hostage to compliance storage). And the record itself had
accreted candidate blocks — composition, policy pins, partition maps — each plausible, none
tested against a rule. This ADR states the rule and the resulting architecture.

## Decision 1 — The receipt carries state, a pin, and a chain. Nothing else.

The working record is:

- **`states`** — the four states themselves. Intent, immutable after submission, travels *in* the
  record; this single fact makes the rest of the design derivable.
- **`resource_type` @ pinned spec version** — the one pin (an existing field). It resolves the
  entire ancestor definition stack through the registry; pin-manifest content digests make the
  resolution deterministic at any future time.
- **`integrity`** — the Layer-1 merkle chain over the state timeline (Decision 2).

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

## Decision 2 — Provenance chains, typed by what they protect

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

**OpenLineage carries the seals** (the adoption disposition and its rationale live in
[`adopted-standards.md`](../../design-principles/adopted-standards.md) §7). What OL lacks is
assigned across the triad — never patched into the standard:

| OL lacks | assigned to |
|---|---|
| tamper evidence | Data — the merkle chains (Decision 4), realizing `AUD-002` |
| completeness + delivery guarantees | Policy + platform — a declared completeness policy; the platform proves emission |
| tenancy + authorization | platform — the ledger store's isolation, never the event schema |
| sovereignty semantics | data itself — residency/classification travel with the record; the Governance Matrix gates emission per facet, tenant, and boundary like any cross-boundary flow |
| identity/attribution (no actor model in OL core) | the `udlm_context` facet, sourced from IdM |

OL-*ingested* lineage (an external platform's events feeding dependency edges) enters as
Discovered, self-asserted tier — an ingestion avenue, never an attested source.

## Findings — ADR-060

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

- **Data (UDLM):** the receipt shape (states + pin + chain); the record-content test and claims
  discipline; the typed-chain model and the seal facet shapes; the Merkle-log *contract*
  (append-only, RFC 9162-verifiable, root externally anchorable — the store is an
  implementation choice).
- **Policy (DCM):** every policy write (sealed); emission completeness and delivery;
  Discovered-seal retention; per-profile posture on pathway continuity citations (provider
  event streams and discovery runs); Governance-Matrix emission gating; the finding policies
  (ADR-060) and response matrix per finding class.
- **Provider:** reports state through the authenticated channels the provider contract already
  obligates (callbacks, lifecycle events); never hashes, never self-declares trust, never
  emits or interprets findings.

## Consequences

- **Pending supersession (executed in the receipt-schema program phase, declared here so the
  inconsistency is never latent):** `realized-entity.schema.json` still carries the in-record
  `provenance` block (#191/E4) and lacks `integrity` — the block's content migrates to the
  `udlm_provenance` facet and the chain block is added when that phase lands; the estate's
  records migrate by idempotent tooling.
- The sealing obligation joins the provider write contract; emission completeness, retention,
  and continuity-citation postures are registered as DCM policy obligations (OBL-003).
- Dashboards, compliance surfaces, and DAV source lineage from the ledger only — rendering
  working-record content under a lineage heading is a defect.

*The one-line summary: best data is none or derivable — and the four states already were the
data.*

# UDLM ADR-041: Policy as information firewall — boundary mediation, structural + value inspection, and the cross-domain guard

**Status:** Proposed (croadfeldt upstream) — companion to ADR-038 §references-context + the projection mechanism (PR #183)
**Date:** 2026-07-22
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)
**Related:** ADR-038 (scoped-Class paradigm; the projection mechanism + `PROJ-P1..P5`); ADR-012 (data-references,
dual anchor); ADR-025 (DCM realization); ADR-008 (the UDLM/DCM peer test); ADR-011 (sovereignty & residency);
`contracts/policy-contract.md` **§2.1** (the policy match sources this extends), **§7** (Evaluation Context); the
`POL` / `TEN` / `SOV` rule families; core-tenets **T2** (transformation is Policy) / **T4** (address ≠ dereference).

**Settles:** in its **information-flow role**, policy **is an information firewall** — it mediates data crossing
boundaries: **directionally** (egress *release* control + ingress *admission* control), on **structure** (the
unresolved reference) or **value** (the resolved datum), backed by a **resolver** and **reactive re-convergence**,
and dialing up to a **sanitizing cross-domain guard** for high-assurance zones. This does **not** touch policy's
second role — assembly / constraint / fill — which is not firewalling.

## Context
The projection mechanism (ADR-038 §references-context, PR #183) lets a resource pull a specific field from a
related entity into its assembly by traversing a classified edge (`self.located-in.network.fabric_id`). That
raised the governance question directly: **does data entering the pipeline by reference or projection bypass or
hide from policy?** Answering it precisely required naming what policy *is* when data flows — and the answer
turned out to be a well-understood object. Policy, in the flow role, has the exact anatomy of a firewall:
directional rules over crossings, matching on headers or payload, stateful, with a default posture. Naming it so
imports a mature discipline (default-deny at trust boundaries, least-privilege, rule-shadowing, the any-any
anti-pattern, exfil-via-allowed-channel) instead of re-deriving it.

The estate is **federated, multi-tenant, and sovereign**: data crosses between authorities, tenants, and
jurisdictions whose policy domains do not trust each other to enforce the other's concern. That is precisely the
setting a firewall (and, at high assurance, a **cross-domain guard**) exists for.

## Decision

1. **In its information-flow role, policy is an information firewall; the unit is the *flow*.** A "flow" is a datum
   crossing a boundary — into a spec (assembly), out to a peer (federation), handed to a provider, or exported
   externally. Policy mediates flows. This is a **structural isomorphism**, not a metaphor:

   | Policy construct | Firewall concept |
   |---|---|
   | Boundary mediation | zone-boundary enforcement |
   | Egress / ingress gates | directional rules (egress vs ingress filtering) |
   | Structural / reference policy | **L3/L4** — match headers (address / authority), not payload |
   | Value / resolved policy | **L7** — deep-packet inspection (the dereferenced datum) |
   | Policy resolver | the inspection engine |
   | Reactive re-convergence | stateful flow tracking / rule reload |
   | Complete-vs-boundary (profile dial) | inspect-every-packet vs stateful-flow; default-deny posture |

   **Scope.** This governs policy's **flow role** only. Policy
   also composes the spec — assembly, constraint-narrowing, policy-fill (ADR-024). That **composition role is not
   firewalling** and this ADR does not restate or constrain it. Same engine, two hats.

2. **Two inspection surfaces — structural and value.** Policy matches on either, and needs both:
   - **Structural / reference (L3/L4).** Match on the **unresolved pointer** — the edge/reference `target`,
     `relation`, `nature`, the **authority in the address**, and a projection's recorded source — **without
     dereferencing**. This is **T4 (address ≠ dereference) cutting both ways**: you can *police the address
     without dereferencing the data*. "Block anything pointing to `dc-east-us`", "no hard dependency crossing
     into `state.wi/*`", "gate any edge to a decommissioning DC" are all structural — no data pulled.
   - **Value / resolved (L7).** Match on the **dereferenced datum** (`residency`, `fabric_id`). Requires the
     resolver (Decision 4) and resolution-before-policy (`PROJ-P1`).
   - **The reference/edge graph is a new policy match source**, added alongside the existing four
     (`contracts/policy-contract.md` §2.1). Structural is cheaper, matches **stable identity** rather than
     transient value, and works when resolution is gated/unavailable — often the surface you want. It also
     **unifies with blast-radius**: "everything that points to X" *is* the `impact_report` graph query, so
     decommission/impact and structural policy share one graph.

3. **Boundary mediation is *directional*: egress (release) + ingress (admission), two owners.** A governed
   crossing is **not one gate** — it is a directional pair enforcing different security properties:

   | | **Egress gate** | **Ingress gate** |
   |---|---|---|
   | Question | "May this data *leave* here, for that destination?" | "May this data *enter* here — do I accept it?" |
   | Owner | the **data owner** (source domain) | the **receiver** (destination domain) |
   | Timing | **before** the crossing — irreversible if skipped | **after** — quarantine / reject on receipt |
   | Property | **confidentiality / release** (Bell-LaPadula-ish) | **integrity / admission** (Biba-ish) |
   | Enforces | **sovereignty, tenancy** (SOV/TEN), classification-out, export | **provenance / FSI**, trust, classification-in, conformance |

   They are **not redundant and neither substitutes**: the source cannot know the destination's admission bar
   (nor is it trusted to enforce it); the destination has no authority over — and arrives too late for — the
   source's sovereignty. Zero-trust ⇒ both gates, each in its own policy domain. **Sovereignty and tenancy are
   inherently egress** (a disclosure that cannot be taken back); **FSI-style acceptance is inherently ingress**
   (the receiver's bar).

4. **A policy resolver, and reactive re-convergence.**
   - **Resolver.** Policy must resolve any datum for inspection — dereference an edge-projected / navigational
     coordinate to the concrete value, on the **same data plane assembly uses**. This is what makes value
     inspection (`PROJ-P1`) real: policy sees `fab-7`, never `self.located-in.…`.
   - **Re-convergence (the outer loop).** Policy is a *settled state over inputs*; when an input changes it must
     re-establish. **Provenance the policy's inputs** (not only spec values): recording each `policy → datum`
     dependency makes that dependency set a **subscription**. A change fires the **same `impact_report` graph** —
     extended to find affected **policies**, not only affected specs — which re-evaluate. Push or pull is a DCM
     implementation choice; the contract only requires the policy→data edges be recorded.
   - **Re-entrant convergence (the inner loop).** Policy application is a **fixpoint, not a single pass**:
     policies **enrich** (looked-up/projected data), **inject** (layer data, defaults), and **mutate** (modify
     fields), and each change means the changed payload must be **re-validated** — evaluate → enrich/inject/mutate
     → re-validate → repeat **until stable and clean**. A single pass would ship the enriched/injected/mutated
     output unchecked. The loop MUST **converge deterministically** — be **confluent** (order-independent result)
     and **terminating** (a bounded fixpoint, no oscillation); the Evaluation Context (POL §7) is the shared
     constraint space that lets policies converge rather than fight. **Determinism is required, not best-effort**
     — it is what makes a request reproducible and replayable (audit; the dual-anchor/rehydration guarantees).
     Enforcing it — cycle / non-determinism **detection** at execution and (where decidable) at policy-injection —
     is the engine's job (**DCM ADR-027**).

5. **Mediation granularity is profile-governed; high-assurance is a *guard*, not a firewall.**
   - **Boundary-mediation by default.** Mediate **crossings** (into-spec, egress-to-peer, provider-handoff,
     external-export), **not** every internal same-boundary read. This gives the data-by-destination guarantee
     without a data-plane chokepoint or availability coupling. *Forcing all data through the policy engine
     regardless of destination is rejected* (see Options).
   - **Profile dial to complete mediation.** A high-assurance / `sovereign` profile may require
     reference-monitor-grade mediation of every access. Model it as **profile-governed strictness**.
   - **The guard.** In the strict mode, policy does not merely permit/deny — it **transforms**: redact, mask,
     constraint-narrow, sanitize. That is a **cross-domain solution (CDS) guard**, the correct reference for
     sovereign/FSI zones. Egress is therefore **field-granular, not binary**: the coordinate lets egress permit
     `dc-east.network.*` while denying `dc-east.location.residency` to a foreign-authority destination — a
     partial release / **firewall rule with a projection mask**.

6. **The projection invariants are this firewall applied to a projection (`PROJ-P1..P6`).** ADR-038 states
   `PROJ-P1..P5`; this ADR adds the ingress half the directional model requires:
   - `PROJ-P1` resolve-before-policy · `PROJ-P2` **egress** gate at the target · `PROJ-P3` mandatory provenance ·
     `PROJ-P4` re-run policy on replay · `PROJ-P5` governed edge-nature.
   - **`PROJ-P6` (new) — ingress admission gate.** A projected/referenced value is **admitted by the receiver's
     ingress policy** (provenance / trust / classification-in), not assumed. `PROJ-P2` was only the egress half
     of the crossing.

## Worked illustrations
- **A projection crosses two gates.** `bm` pulls `dc-east.location.residency` via `located-in`.
  **Egress at `dc-east`** (`PROJ-P2`): may residency be *released* to `bm`'s authority? — sovereignty/tenancy,
  the owner's call, pre-crossing. **Ingress at `bm`** (`PROJ-P6`): does `bm` *admit* it? — provenance/trust, the
  receiver's call, on arrival. Two owners, two properties; the value lands only if both pass.
- **Structural policy, no dereference.** "No resource may hold a `hard` dependency whose target authority is
  outside `state.mn/*`." Evaluated purely on the edge's `nature` + the **authority in the target address** — the
  data is never resolved; sovereignty is enforced on the pointer (an L3/L4 rule).
- **Field-granular egress (the guard).** A peer requests `dc-east`. Under the `sovereign` profile the egress
  guard **releases** `network.*`, **redacts** `location.residency`, and **denies** `power.*` — one crossing,
  three field-level dispositions, all recorded in provenance.

## Data · Policy · Provider
- **Data** — the flows and their provenance (spec-value provenance *and* policy-input provenance).
- **Policy** — the firewall/guard itself: the decision over every crossing. This ADR *is* the Policy leg for the
  flow role.
- **Provider** — the endpoints a flow crosses to/from; realization honors the disposition (released / redacted /
  denied) the guard emits.

## UDLM vs DCM — what lands where (the peer test, ADR-008)
| Piece | **UDLM** — model / grammar / data (a peer MUST honor) | **DCM** — engine / decision (a peer MAY differ) |
|---|---|---|
| **The firewall contract** | flow as the unit; the structural + value match surfaces; the reference/edge graph as a match source | the enforcement engine at each crossing |
| **Directional mediation** | the egress/ingress **structure**, owners, and required-both rule | which gate fires, the actual release/admit decision |
| **Resolver** | the requirement that policy inspects concrete values (`PROJ-P1`) | the resolver implementation, shared with assembly |
| **Re-convergence** | policy-input provenance is recorded; a change re-evaluates dependents | the reactive engine (push/pull), the graph walk |
| **Strictness** | strictness is **profile-governed**; the guard/transform + field-granular-egress **grammar** | the guard implementation (redact/mask/sanitize), the posture |
| **Invariants** | `PROJ-P1..P6` (what must hold) | enforcing them at realization |

**One line:** UDLM owns the **firewall contract** — the surfaces, the directional structure, the invariants, the
guard grammar; DCM owns the **engine** — the resolver, the reactive re-convergence, and enforcement at each
crossing.

## Options considered
- **(A) Force all data through the policy engine regardless of destination** (universal reference-monitor
  mediation). *Rejected* — a data-plane chokepoint, availability coupling (no resolve without policy up), and it
  blurs the Data·Policy line (policy becomes part of *resolution*, not a *decision over* it). Boundary-mediation
  gets the data-by-destination guarantee without the cost; the profile dial serves those requiring complete mediation.
- **(B) Value inspection only** (resolve everything; policy on values). *Rejected* — loses structural policy
  (jurisdiction / decommission / trust on the pointer), and forces resolution even when it is gated, unavailable,
  or expensive.
- **(C) A single undirected boundary gate.** *Rejected* — egress and ingress are different properties
  (confidentiality vs integrity), owned by different domains; collapsing them breaks the federated trust model.
- **(D) [chosen]** The information-firewall contract: structural + value surfaces, directional egress/ingress,
  resolver + reactive re-convergence, profile-dialed guard with field-granular egress.

## Consequences
- Policy review inherits the **firewall/guard discipline and failure-mode catalog** — default-deny at trust
  boundaries, least-privilege rules, rule-shadowing, the any-any anti-pattern, exfil-via-allowed-channel.
- The **reference/edge graph becomes a first-class policy input**; this depends on the classified-edge model
  (ADR-038 §references-context / the pending edge reframe).
- **Field-granular egress / partial-release** is the one net-new mechanism — a firewall rule with a
  projection mask, expressed on the §10 coordinate.
- Re-convergence requires extending **provenance from spec values to policy inputs**.
- Ties **sovereignty & tenancy** to concrete **egress** gates and **FSI / trust** to concrete **ingress** gates —
  making the earlier profile work (sovereign / FSI) enforceable at named points rather than by prose.
- **`PROJ-P6`** closes the ingress half of the projection crossing that `PROJ-P2` left open.

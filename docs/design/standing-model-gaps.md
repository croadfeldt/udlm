# Standing model gaps — the open holes, with a proposal for each

**What this settles:** nothing by itself. This note collects the model gaps that the corpus and the
probe campaigns have surfaced and left *without a ruling*, and proposes a closure for each — the
demand, what the registry carries today (named file and field, checked against the current tree),
two or three candidate shapes with their costs, a recommendation with its reasoning, and the corpus
case that would prove it. Every recommendation is a proposal awaiting a maintainer ruling. Where a
proposal adds a resource type, the type is **sketched** — family, key spec fields, outputs,
relationships — never authored: authoring follows the ruling, with its use cases, per the base
standard (`registry/SPEC-DESIGN-REQUIREMENTS.md` rule 36 — a type ships with a worked example and
corpus use cases or it is not done).

**Where the demands come from.** Three independent passes, none of them speculative: the layer-2
expressibility analysis of the 28-use-case corpus (every `success_criterion` treated as one demand
against the registry surface); a cross-walk of the Kubernetes core/apps API against the type set,
which flags portable intent the model cannot carry; and the estate-payload replay that validates
real discovered records against pinned specs, which produced issue #239. A gap with no use case and
no filed issue behind it is not in this note.

**Two of the seven arrived already narrowed, and the note says so rather than restating the audit's
snapshot.** The output-exempt discriminator is materially closed by gates that landed on
2026-07-25; rebuild lineage turns out to be *ruled* already, with only the schema realization
missing. Both entries below are rewritten to the residue that actually remains.

## Summary

| Gap | Demand | Recommendation | Corpus case | Blocked on |
|---|---|---|---|---|
| Backend-pool consumer surface | `binding-surface/001` — bind a consumer to a producer's realized addresses; corroborated by the Kubernetes Ingress cross-walk (no route surface anywhere) | Sketch a `Network.Route` type adopting the Gateway API's route/backend shape; backend members carry the bindable address/port fields a `binds_to` edge can target | `binding-surface/001`, re-run with a registered consumer instead of a hypothetical one | Ruling only |
| Worked-example linkage | `binding-surface/004-worked-example` — every type has a current worked example, staleness mechanically detectable | Do **not** add a pointer to the type; invert it — examples declare their type and version already, so derive per-type coverage and staleness in `model_health.py` and let the deferred G4 gate enforce it | Same case, judged on a derived coverage report rather than 48 hand reads | Ruling; then an example burn-down (10 record-kind examples against 48 types) |
| Rebuild lineage | `bare-metal/002`, `multi-cluster/004` — a rebuilt entity states what it replaced | Realize the *existing* ruling: `RHY-005` names `source_store` / `source_record_uuid` / `provider_entity_id_history`, and no schema carries them. Put the pair on the state snapshot beside `origin` | `bare-metal/002` — rebuild under a new uuid, then resolve the predecessor from the record | Placement ruling only (the shape is already decided) |
| Reference authority | `must-reject/002` — refuse an egress by matching the *target authority in the reference*, without dereferencing | Add an authored `target_authority` to the canonical `Reference`, shaped as the addressing coordinate's dotted routing authority; absent means the local estate | `must-reject/002` — the refusal must be reachable with the pointer unresolved | **CLOSED** — shape A landed with the ADR-051 alignment change (`common-elements.schema.json` `$defs/Reference.target_authority`, shipped in the same MINOR as the pin fields so the Reference shape moved once); §4 below records the pre-ruling analysis |
| Reduction disclosure | `must-reject/006` — a policy-reduced response says it was reduced, without leaking what it hid | Split it: define a portable disclosure element now (states *that* a reduction happened, and under which policy); defer the *which paths* half | `must-reject/006` read half — a reconciler must not read absence as ground truth | Disclosure: ruling. Path enumeration: **P0**, the class system's coordinate grammar |
| Output-exempt discriminator | `binding-surface/002` (met today), `/003` (partly met) | Keep the prose rationale; add one enumerated exemption marker so the gate binds positionally, the scoreboard can classify declared/exempt/gap, and a *deferred* exemption stops reading as a permanent one | `binding-surface/003` — the classification comes from the registry, not a hand list | Ruling on whether the marker earns a meta-schema field |
| Processor aggregate surface | Issue #239 — real records carry a host-level socket count the spec cannot express | Documented exclusion: the count already lives on the host rollup (`Compute.BareMetalHost.spec.cpu.sockets`), which is where the component-granularity rule puts it; ingest maps it there | A discovery/drift case for `Hardware.Processor`, which no use case currently exercises | Ruling; closes #239 either way |

---

## 1. A consumer for the flagship binding

**The demand.** `use-cases/binding-surface/001-typed-outputs-declared-per-type.yaml` opens with a
platform engineer binding "a consumer (a load balancer backend pool) to a producer's realized facts
(a VM's addresses)". The producer half is in good shape — `Compute.VirtualMachine` publishes
`primary_ip`, `ip_addresses`, `mac_addresses` and six more typed outputs, and the catalog item's
`bindings[]{from_component, output, to_field}` resolves against that declaration. The consumer half
has no registered type: the family's flagship binding has nothing to bind *into*. The Kubernetes
cross-walk reached the same hole from the other side — host and path routing (`Ingress`, and the
Gateway API's route objects) is portable intent that every load balancer, cloud service, and reverse
proxy carries, and the registry has no surface for it.

**What exists today.** `registry/resource-types/network/network.gateway.json` (0.4.4) declares an
`l7-proxy` value in `functions`, but its whole spec is `functions`, `segments`, `ip_family` and its
single output is `external_address` — there is no member, backend, or route field a binding's
`to_field` could name. `registry/resource-types/software/software.service.yaml` carries `endpoints[]`
(`name`, `port`, `url`), described as informational and naturalized from the provider — a description
of where a service *is*, not a declaration of what a front end should send traffic to.
`Network.IPAddress` and `Network.IPAddressPool` cover the virtual address; nothing covers the pool of
members behind it.

**Candidate shapes.**

- **A. Extend `Network.Gateway` with a route/backend block.** Smallest diff, and the type already
  claims `l7-proxy`. The cost is conceptual: the type's own description says it is deliberately
  L3/edge — router, NAT, firewall — and "broader than the Gateway API's L4/L7 service focus".
  Folding L7 routing into it makes one type mean two things and makes its `functions` enum
  load-bearing for which half of the spec applies.
- **B. A `Network.Route` type adopting the Gateway API's route/backend shape** (recommended). The
  industry has already done this split — a Gateway is the listener/address, a Route is the
  match-and-forward rule with its backend references — and adopting it by reference is the tenet
  the registry already applies to `Network.Gateway`. Backends become the consumer surface: a member
  entry references a producer and carries the address and port fields a binding writes into.
- **C. A `Network.LoadBalancer` type.** Matches how operators speak, but names a *mechanism* rather
  than the intent: a load balancer is one realization of "route these requests to these members"
  alongside a cloud service, a proxy, and a mesh. The reference-discipline lesson — requirements and
  references, never the vendor-native or mechanism-native noun — argues against making the mechanism
  the type.

**Recommendation: B.** It satisfies adopt-by-reference (a credible external standard already solved
route-to-backend), it keeps `Network.Gateway` honest about being L3/edge, and — the decisive part —
it produces a *field a binding can target*, which is what the use case actually fails on today.
Sketch, for the ruling to accept or reshape:

- **Family** `Resource`; **portability** portable; **name** `Network.Route`.
- **Spec:** `protocol` (a small enumerated set, HTTP/TLS/TCP/UDP); `hostnames[]` and `path_matches[]`
  (the portable half of the Ingress cross-walk); `listener` — a `Reference` to the `Network.Gateway`
  or `Network.IPAddress` that fronts it; `backends[]` — each `{member_ref: Reference, address, port,
  weight}`, where `address`/`port` are the **bindable** fields (a catalog binding writes the
  producer's `primary_ip` into `backends[].address`, contract-checked against the producer's declared
  outputs) and `member_ref` records which entity the value came from, so the graph carries the edge
  rather than a spliced string.
- **Outputs:** `serving` (state), `resolved_backends` (count or member list as realized), and the
  effective front-end address when the route owns one.
- **Relationships:** `binds_to` the producers (VM, container, service) — the edge the use case
  demands; `references` the gateway or address that fronts it; `references` a
  `Security.CredentialRef` for TLS material, which the cross-walk found already expressible.
- **Exclusions to document:** controller-specific rewrite, timeout, and body-size annotations
  (per-controller vocabulary — the canonical-accretion trap), session affinity and external traffic
  policy (realization mechanics), and class selection (a realized fact, not portable intent).

**Corpus case.** `binding-surface/001` re-run against a registered consumer, plus the two the base
standard would require with the type: a portability case (the same route intent realized by two
different providers) and a rehydration case (the route rebuilds and re-binds to the replacement's
new addresses). No issue is filed for this today.

---

## 2. Worked examples: stop pointing, start deriving

**The demand.** `use-cases/binding-surface/004-worked-example-currency-per-type.yaml` asks that every
registered type have at least one worked example, that the example validate against the type's
current spec version, and that staleness — fields the spec added and the example never grew — be
mechanically detectable rather than discovered by a confused adopter.

**What exists today.** `registry/resource-type-spec.schema.json` has 22 top-level properties and none
of them is an example linkage (the `example` string that appears in it is the relationship-enforcement
enum, unrelated). `registry/instances/` holds roughly forty files, but they are *record-kind*
examples — a layer, a policy, an audit record, a catalog item — against 48 resource types, and the
per-type worked examples live as prose in `docs/examples/`. `tests/check_type_standard.py` says so in
its own docstring: gate G4, worked-example currency, "is deferred pending the example-bar ruling; the
exists-half is reported informationally, never failing."

**Candidate shapes.**

- **A. An `examples[]` element on the type spec** — each entry a path or `$id` pointing at the
  instance that demonstrates the type. Direct, and it answers "a type cannot point at its example".
  The cost is that it stores a fact the model can already compute: an instance record declares
  `resource_type` and pins `type_version`, so the type→example relation exists in the data and a
  stored copy of it is a second home that goes stale the first time an example is renamed or
  retired — precisely the drift the compute-never-store rule exists to prevent.
- **B. Derive coverage and currency from the examples themselves** (recommended). Every realized-entity
  example already carries `resource_type` + `type_version`; `registry/tools/model_health.py` already
  scores per-type coverage on two other axes (use-case coverage, consumer coverage) and would gain a
  third — examples present, and whether the pinned `type_version` equals the type's current version.
  Staleness becomes a computed distance, not an assertion, and G4 flips from informational to
  enforcing once the burn-down is done.
- **C. A filename convention plus a gate** (`registry/instances/<type>.example.yaml`). Cheap, but it
  makes navigation identity-bearing, which the registry has explicitly refused elsewhere — the
  resource-types README states that directory location is navigation, never identity.

**Recommendation: B**, with one deliberate exception. Coverage and currency are derivable and should
be derived. The single fact that is *not* derivable is curation — which of several examples is the
canonical "start here" for an adopter. If the maintainer wants that, it is one optional pointer on
the type, justified as a curation decision rather than a duplicated relation, and it should be worded
so it can never be read as the coverage source.

**Corpus case.** The same `004-worked-example` case, judged on a derived report: a newly registered
type appears as an example gap immediately, and an example pinned to a superseded `type_version`
appears as stale — both without a hand-maintained list. The honest prerequisite is that the examples
have to exist: 48 types against roughly ten record-kind examples is a burn-down, and the ruling should
say whether every type owes one or whether some families are exempt by nature (the same
exempt-versus-gap question section 6 asks about outputs, and the answers should match).

---

## 3. Rebuild lineage — the ruling exists; the schema does not carry it

**The demand.** `use-cases/bare-metal/002-host-rehydration-replay-intent.yaml` requires that "lineage
from the replacement to the original is recorded (rebuild-from-intent semantics, new correlation
identity)", and `use-cases/multi-cluster/004-self-managed-hub-rehydration.yaml` requires that "hosted
spokes rebuild from their own intent with lineage to the originals".

**What exists today — and this is the part that changes the framing.** The decision has already been
made. `foundations/four-states.md` §5.2 rules that a *restore in place* preserves the entity uuid
while a *rebuild from intent* is a new entity with a new uuid, "kept traceable to its source by
lineage", and then states the mechanism: "lineage rides the general provenance model: `rehydration`
is a provenance `source.kind`, and the new Intent records `source_store` / `source_record_uuid` for
the record it was rehydrated from … the data model needs no separate rehydration-history structure."
Rule `RHY-005` in the same file carries it normatively, naming `provider_entity_id_history` for the
restore-in-place half.

The schema realizes half of that sentence. `registry/realized-entity.schema.json` has `rehydration`
in the provenance `source.kind` enum — and a repository-wide search finds `source_store`,
`source_record_uuid`, and `provider_entity_id_history` in **no** schema at all. So this is not an open
design question; it is normative prose that no record can express. The layer schema's `supersedes[]`
is a different mechanism for a different object (immutable reference-data versions) and should not be
mistaken for the answer here.

**Candidate placements** (the shape is ruled; only the home is open).

- **A. On the state snapshot, beside `origin`** (recommended). `$defs/state_snapshot` already carries
  `origin` — "how this snapshot came to be", an extensible enum of `declared`,
  `discovered-derived`, `backfilled` — which is exactly the question lineage answers. Add
  `rehydrated` to that enum and a `source_record: {store, record_uuid}` sibling. This matches the
  ruling's own words (*the new Intent records* the source), keeps the fact at snapshot grain where
  the Intent that replayed it lives, and is purely additive.
- **B. An entity-level `rehydrated_from` block.** Easier to query — one lookup, no snapshot walk —
  but it hoists a per-replay fact to the entity, and an entity rebuilt twice would need it to become
  a list, which is the rehydration-history structure the ruling explicitly declined.
- **C. Extend the provenance `source` object** with the two fields. Consistent with `kind:
  rehydration` living there, but provenance is keyed by dot-path into the spec — field grain — and a
  rebuild is a whole-entity event. Recording it per field would repeat one fact across every field
  in the record.

**Recommendation: A**, plus `provider_entity_id_history` for the restore-in-place half of `RHY-005`,
which today has the same problem for the same reason. Two notes for the ruling. First, this touches
the versioning epoch's provenance contract (ADR-045 §7 — every realized instance carries realization
provenance naming the class, provider, and engine revisions that governed it): rebuild lineage is a
*different* axis and must not be folded into it. Realization provenance answers "what governed this
realization"; lineage answers "what did this replace". The rebuilt entity has fresh realization
provenance by construction — that is the point of replaying intent — so a reader who conflates them
will conclude, wrongly, that the predecessor is unrecoverable. Second, the corpus's phrase "new
correlation identity" is already satisfied: `correlation_ids[]` carries the replacement's discovered
natural keys, and the lineage pointer is what keeps the dead host's record reachable from the new one.

**Corpus case.** `bare-metal/002`: replace a failed host, provision from the stored intent, and
resolve the predecessor's record from the replacement without consulting anything outside the estate.
`multi-cluster/004` exercises the same pointer across a hub rebuild.

---

## 4. Which authority owns the target

**Status: CLOSED.** Recommendation A was adopted and shipped with the ADR-051 alignment
change: `$defs/Reference` now carries the optional authored `target_authority` (dotted
ADR-038 §10 form, absent = the local estate, shape constrained / reachability never), landed
in the same MINOR as the `target_version`/`target_digest` pin fields so the canonical
reference shape evolved once. The analysis below is retained as the record of how the ruling
was reached.

**The demand.** `use-cases/must-reject/002-sovereignty-egress-refused.yaml` requires the refusal to be
reachable *before* anything is dereferenced: "the structural surface is sufficient to refuse — the
decision matches on the target authority in the reference, without dereferencing the protected data".
The point is not the refusal; it is that resolving the pointer in order to decide whether resolving
the pointer is allowed defeats the purpose.

**What exists today.** `registry/common-elements.schema.json` `$defs/Reference` carries exactly three
properties: `target_handle` (the authoring key), `target_uuid` (resolution provenance, system-populated
at reserve), and `resource_type`. Nothing in the address says which estate, peer, or jurisdiction owns
the target. `registry/data-reference.schema.json` — the *other* reference shape, pointing at
immutable reference data — does carry `resolving_authority` and `residency`, but both are explicitly
marked resolution provenance, "NOT consumer-authored", recorded by the control plane at resolution.
Provenance is written after the crossing the use case exists to prevent.

Meanwhile the doctrine has already moved: ADR-041 (policy is an information firewall — boundary
mediation with structural and value inspection) names "the **authority in the address**" as a
first-class structural match surface, the cheap L3/L4 half of the analogy, matched "without
dereferencing"; and ADR-038 §10 defines the addressing coordinate as `[<authority>/]<anchor>.<field-path>`
with an extensible routing-root registry (`peer`, `tenant`, `jurisdiction`) and a dotted, filterable
authority. Two ratified-track documents describe policy matching on a field the canonical reference
shape does not have.

**Candidate shapes.**

- **A. `target_authority` on `Reference`** (recommended) — an authored, optional dotted string in the
  §10 routing-authority form, absent meaning the local estate, with the same authoring discipline as
  `target_handle` (a human writes it; the control plane never invents one).
- **B. A single `target_address` carrying the whole §10 coordinate as one string.** Fewer fields,
  and it aligns the reference with the addressing grammar in one move — but it makes every consumer
  parse a composite to filter on the authority, and string-splicing is what typed references exist to
  end.
- **C. Match on the resolved target's tenant and residency instead.** Requires no schema change and
  fails the use case outright: those values exist only after resolution.

**Recommendation: A**, with two constraints for the ruling. The value is a *logical* authority name
— the federation-resolution ADR is explicit that mapping it to a reachable resolver is control-plane
policy and never public DNS — so the schema should constrain its shape and never its reachability.
And the field must be non-leaking by construction: an authority name identifies a boundary, not the
data behind it, which is what lets the refusal name the boundary it hit while satisfying the same use
case's requirement that the refusal payload enumerate nothing protected.

This also settles a smaller thing worth stating plainly: ADR-040, the federation-resolution stub,
defers its mechanics as "demand-driven, starting with the `peer` root". `must-reject/002` is that
demand, and it needs only the naming half — a reference that can *say* which authority owns its
target — not the resolution half the stub defers.

**Corpus case.** `must-reject/002`, judged on whether the refusal is decidable with the pointer
unresolved. The negative case matters as much: a same-authority reference must not become
authority-bearing noise, so the absent value has to mean the local estate and nothing else.

---

## 5. Disclosing a reduction — one half is authorable, one half is P0

**The demand.** `use-cases/must-reject/006-masked-projection-write-refused.yaml` is explicit that the
read half is a guard, not a binary gate: the response "omits or masks the excluded field AND states
that the projection was reduced by policy — a silently-shrunk projection is a failure, because the
consumer would treat absence as ground truth (a reconciler that reads a silently reduced projection
and writes it back would erase the field)". The write half — refusing the round-trip — is the
must-reject, and it is already expressible.

**What exists today.** The *decision* vocabulary is in place: `contracts/policy-contract.md` §15
defines a boundary-control output with `decision: ALLOW | DENY | ALLOW_WITH_CONDITIONS | STRIP_FIELD
| REDACT | AUDIT_ONLY`, a `field_permissions` block (`mode`, `paths`, `on_blocked_field`), and
`audit_on` including `STRIP_FIELD`; `registry/policy.schema.json` carries the same surface. So policy
can *decide* to reduce, and the audit trail records that it did. What no schema carries is the
statement travelling **with the reduced response** — the words "reduced" and "mask" appear in no
registry schema. The consumer that must not mistake absence for ground truth is exactly the party
the current model never tells.

**Candidate shapes.**

- **A. A portable disclosure element in `common-elements.schema.json`** (recommended for the half
  that is authorable now) — a small shape a response carries: that a reduction occurred, the
  governing policy or scope identity, and the disposition (omitted versus masked-in-place). Path
  enumeration is *not* in the floor, and that is a design decision rather than an omission: the
  sibling case `must-reject/002` requires refusals that "do not enumerate protected content", so a
  disclosure that always listed the reduced paths would leak the shape of what it protects. The floor
  is "this response is not complete, and here is who decided"; path detail is a profile-gated
  addition for estates where the consumer is trusted with it.
- **B. A marker on the realized entity.** Wrong object — a reduced projection is a response served to
  a caller, not a stored state of the resource. Marking the record would make one caller's reduced
  view a property of the entity itself.
- **C. Leave it entirely to the control plane's response and error model.** Tempting, since
  `contracts/error-model.md` already owns the error envelope. The cost is portability: a consumer
  reading two conformant peers would learn reduction from each in a different way, and ADR-041's own
  boundary table assigns UDLM "the guard/transform + field-granular-egress **grammar**" while leaving
  the guard implementation to the control plane. The grammar is this shape.

**Recommendation: A for the disclosure floor; defer the path-enumeration half.** And this is the one
place in this note where a gap is genuinely blocked on the class system (issue #230). ADR-041's own
consequences put the field-granular mask "expressed on the §10 coordinate" — the addressing grammar
that the scoped-Class realization owns and that has no machine surface today. **The contract P0 must
satisfy for the deferred half to close:** a machine-validatable form for the §10 coordinate — a
declared grammar plus a validator that can accept or reject a coordinate string against a type's
element set — so a mask can name reduced locations portably, a disclosure can cite them without
restating hand-written schema paths, and a consumer in another estate can interpret them without
knowing the producer's internal spec layout. Until that exists, any path list here would be free
strings, which the reference discipline refuses.

**Corpus case.** `must-reject/006`, read half only: a caller with a reduced scope reads the resource,
and a reconciler consuming the response can tell it is incomplete without being told what is missing.

---

## 6. Zero outputs: mostly closed, and the residue is worth naming

**Honest status first.** The audit recorded this as a missing discriminator — nothing distinguished a
type with legitimately empty outputs from one that forgot. That is no longer true. `tests/check_type_standard.py`
gate G1 fails any `Resource`- or `Process`-family type declaring zero outputs unless the document
carries an `outputs-exempt:` rationale, and the baseline it ratchets against is empty, so the gate is
live rather than deferred. `tests/check_derivability.py` (the derivability gate that landed the same
day) adds the neighbouring vocabulary: an aggregation-shaped output must declare itself `DERIVED`
with its source or `OBSERVED`, or the type must carry the same exemption token. The first demand —
`binding-surface/002`'s "types with legitimately empty outputs are distinguishable from types that
merely forgot" — is **met today**, and the six zero-output types split cleanly: three `Knowledge`
records, and `Automation.Job`, `Hardware.Processor`, `Hardware.GraphicsProcessor` all carrying
written exemptions.

**What actually remains** — three things, all small, all real.

- **The marker is positionally unbound.** G1 tests for the token in `json.dumps(d)` — the whole
  serialized document. A type satisfies the gate with the token sitting in an unrelated field
  description, and a type that *moves* its rationale into a place no reader looks still passes.
- **The classification is not a classification.** `binding-surface/003` asks for every type to be
  "classified: outputs declared, exempt-by-family, or gap", derived from the registry.
  `registry/tools/model_health.py` reports zero-output and one-output type *lists* — six and
  twenty-three respectively — with no exempt/gap split, because splitting them means parsing prose.
- **Exemptions differ in kind and nothing says which.** `Hardware.Processor`'s exemption is permanent
  by nature — an opaque inventory component whose attributes are discovered facts on its host.
  `Automation.Job`'s is a *forward pointer*: run-history facts belong to a run instance, and "the run
  instance type (Process family) declares these outputs" — a type that is not registered. That is a
  deferral wearing an exemption's clothes, and today they read identically.

**Candidate shapes.**

- **A. Keep everything in prose; tighten the gate.** Scope G1's token search to the metadata
  description and the context purpose, and teach the scoreboard to split declared/exempt/gap by
  looking there. Zero schema change. It leaves the deferred-versus-permanent distinction
  unrepresentable and keeps a machine classification dependent on prose parsing.
- **B. One enumerated marker on the meta-schema** (recommended) — an `outputs_exempt` object whose
  `kind` distinguishes exempt-by-nature from deferred-pending-a-type, with an optional pointer to the
  type or issue the deferral waits on. The human rationale stays in the description where it reads
  well; the machine reads one field.
- **C. Derive exemption from family.** The cleanest-sounding option and it under-determines the
  answer: `Knowledge` types are exempt by family, but `Automation.Job` (Process) and the two
  `Hardware` components (Resource) are legitimately exempt too. Family alone would flag three
  correct types as gaps.

**Recommendation: B.** The reduce-to-existing test is what makes this a proposal rather than an
obvious add — the honest answer is that no existing element carries *why a type publishes nothing*,
and the fact the residue needs is not derivable from anything the registry holds. The payoff is
proportionate: the gate binds to a field instead of a substring, the scoreboard classifies without
reading prose, and a deferred exemption becomes a burn-down item with a named blocker rather than a
permanent-looking claim.

**Corpus case.** `binding-surface/003` — the classification comes from the registry and a newly
registered realizable type with no outputs appears as a gap immediately. A second, sharper case is
worth adding: an exemption that points at an unregistered type should surface as *deferred*, not as
settled, which is the `Automation.Job` situation today.

---

## 7. The processor aggregate (issue #239)

**The demand.** Issue #239, from the estate-payload replay: five real processor records carry a
host-level socket count that `Hardware.Processor` cannot express. The issue itself names the three
candidate outcomes — an aggregate surface on the type, a host-level home elsewhere, or a documented
exclusion — and leaves them for a ruling.

**What exists today.** The host-level home already exists.
`registry/resource-types/compute/compute.bare-metal-host.json` carries `spec.cpu` as a reconciled
rollup — `sockets`, `cores`, `threads` — adopting Redfish `ProcessorSummary`, with `sockets` mapped
to `ProcessorSummary.Count`. The guest side is covered too: `Compute.VirtualMachine.spec.vcpu` carries
`count`, `sockets`, `cores_per_socket`. `Hardware.Processor` 0.2.2 models one processor — `cores`
(required), `threads`, `architecture`, `max_speed_mhz`, with `identity.location` as the socket
designation — and is `contained_by` its host.

**Candidate shapes.**

- **A. Documented exclusion, with ingest mapping to the rollup** (recommended). The
  component-granularity rule (`SPEC-DESIGN-REQUIREMENTS` §26) is direct about this: the parent always
  carries the rollup, a component may *also* be a first-class entity contained by it, and a mismatch
  between the two is drift. A socket count is the parent's fact; it already has a home; a
  source-reported per-record copy maps there at ingest, which is provider naturalization rather than
  a model field.
- **B. Add `socket_count` to `Hardware.Processor`.** It matches the incoming payload one-for-one and
  costs the model two things it does not want to spend: a second home for one fact (the reconciled
  rollup and the per-record copy will diverge, and §26 calls that divergence drift), and a component
  record that describes its siblings rather than itself. It is also derivable — counting the
  processor records contained by the host — which the compute-never-store rule refuses to duplicate.
- **C. A Redfish-`ProcessorSummary`-shaped block on the component.** Same objections as B, plus it
  adopts a standard's *summary* object onto the standard's *member* object, which the standard itself
  does not do.

**Recommendation: A**, and #239 closes on the ruling either way — the issue asks for a decision, not
necessarily a field. Two things belong in the closure so the finding does not regrow: a `not_for`
line on `Hardware.Processor` saying aggregate socket counts are the host's rollup, and a note in the
issue that the ingest side owes a mapping rule (a source-reported socket count lands on the host's
`cpu.sockets`, where a mismatch against the counted component records is reportable drift).

**Corpus case.** There is none today, and the scoreboard says why: 43 of 48 types appear in no use
case, `Hardware.Processor` among them. The case to write is the discovery one this finding implies —
a host is discovered, its component records and its rollup are both populated, and a disagreement
between them surfaces as drift rather than as a silently preferred number.

---

## What this asks for — the ruling surface

Seven decisions, each independently rulable:

1. **A route/backend consumer type** — accept the `Network.Route` sketch (or redirect to extending
   `Network.Gateway`), then author it with its use cases per rule 36.
2. **Worked examples: derive or point** — derived coverage and currency in the scoreboard, with G4
   promoted from informational to enforcing after a burn-down; plus whether a curated "canonical
   example" pointer is wanted, and which families are example-exempt.
3. **Where rebuild lineage lands** — the state snapshot beside `origin` (proposed), an entity-level
   block, or the provenance source. The shape is already ruled by `RHY-005`; this is placement, and
   the three named fields need a schema home either way.
4. **An authored authority component on `Reference`** — and confirmation that it is a logical routing
   name whose resolution stays with the federation-resolution ADR.
5. **A portable reduction-disclosure element** — and confirmation that the path-enumeration half
   waits on the class system's coordinate grammar, with the contract stated in section 5.
6. **Whether the output exemption earns a meta-schema field** — one enumerated marker (proposed)
   against a tightened prose gate.
7. **The processor aggregate** — documented exclusion (proposed) against a field on the component;
   #239 closes on the answer.

## Cross-check against the filed issues

| Issue | Relation to this note |
|---|---|
| #239 — Hardware.Processor has no aggregate/socket-count surface | **Closed by section 7** on either ruling; the proposal is the documented exclusion plus an ingest mapping note |
| #230 — class-system realization program | The blocker section 5 names: the deferred half of reduction disclosure needs the addressing coordinate to be machine-validatable |
| #241 vCPU hot-resize ceiling · #243 day-0 bootstrap · #244 thin-provisioning intent | The VM intent-completion set — field rulings on `Compute.VirtualMachine`, not proposed here |
| #242 — CPU passthrough/mode intent | Same VM set, but it shares section 5's dependency: the type's own spec defers it to a Provider-Class element, and that carrier is unrealized |
| #250 — no DR-pairing/replication surface on Storage types | The same shape as section 1 — a consumer/relationship surface the corpus demands and no type declares — in a different family; not closed here |
| #251 — Storage.FileShare outputs too thin for cutover verification | Adjacent to section 6 and deliberately not closed by it: the discriminator classifies *zero*-output types, while #251 is one-output adequacy, which nothing scores. Section 6's classification would make the class visible; judging adequacy remains a review question |
| #253 — `resources.cpu` typed string in one type, number in another | A shared-element question — the same concept defined independently per type is what the scoped-Class work exists to fix; untouched here |

Six of the seven gaps in this note have no issue filed. A ruling on any of them should either open one
or record the decision here, so the next sweep finds the answer rather than the gap.

# UDLM ADR-049: Credential material at intent intake — the rejecting path must not be where the secret lands

**Status:** Proposed (croadfeldt upstream) — pending engineering ratification (#217); **decided 2026-07-28 (maintainer, ADR-008 peer test): the invariant is UDLM; the enforcement mechanism and its rigor are delegated to policy/profile — a DCM obligation, tracked in the DCM policy-obligations register.** The mechanism catalogue below is *informative* — shapes an implementation may implement, not a choice UDLM makes.
**Date:** 2026-07-25
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)
**Background — read first (the cold reader's on-ramp; skip if you have the context).** Each cited
once with what it settles. `governance/credentials.md` — **CPX-001** (values never rest in the
implementation's stores) + **CPX-013/CPX-014** (the intake detection + non-persistence rules this ADR
picks the mechanism for). `foundations/four-states.md` — Intent is the *immutable* record of what
was asked for, the constraint that makes this a design question, not a cleanup task.
`registry/classes/resource/security/credential-ref.yaml` — the reference type (names which credential
is held where; no value field). `registry/SPEC-DESIGN-REQUIREMENTS.md` §36(h) — the authoring-time
twin (review can't see a value a submitter supplies at run time). ADR-039 /
`docs/design/vocabulary-intake-ladder.md` — the match/mint ladder, the model's precedent for
*changing* a submitted value at intake, not just judging it. `contracts/error-model.md` §8a — a
refusal is itself a boundary crossing.
[`use-cases/must-reject/003-inline-credential-literal-refused.yaml`](../../use-cases/must-reject/003-inline-credential-literal-refused.yaml)
— the case that measures this.

## Context

The model's secrets discipline is a good one and it is complete on the axis it addresses: a
credential's *value* lives with the credential provider, the data model carries a reference, and
no profile relaxes that. The discipline assumes, reasonably, that values are things the substrate
*handles* — issued, rotated, retrieved — and it governs where handled values may rest.

It does not cover the case where a value arrives somewhere no one intended it to be. A consumer
writing an intent by hand, or generating one from a system that already holds the secret, pastes
a database password into the field that expects a credential reference. Nothing catches it. A
secret and a reference to a secret are both strings; the schema constrains the field to a string;
the intent is well-formed. Detection exists in this model, but on two side doors — a secrets
scanner over the GitOps store, and a plaintext check on auth-provider registration payloads —
neither of which is on the consumer intent path. What that path does catch is a dangling
reference, and it reports it as a dangling reference: a message about an unresolvable name,
telling the submitter nothing about the fact that they have just transmitted a live credential.

The hard part is not detection. It is that the path which *rejects* the request is also the path
that stores it. The Intent record is written verbatim and never modified afterwards — that
immutability is deliberate, it is what makes "what was actually asked for" answerable months
later, and in an implementation it is enforced at the storage layer by revoking update and delete
rather than by convention. So an intent containing a pasted password, refused for containing a
pasted password, is nonetheless *persisted with it*, permanently, in the store whose whole
guarantee is that nothing can take it back out. There is no scrub step to add. The refusal
becomes the leak, which is exactly the failure the must-reject case names — and the case is right
to insist that a nominal rejection is not a passing outcome.

Two smaller pressures sit alongside it. Refusal payloads that quote the offending value back
"to help the submitter find it" copy the secret into the error channel and into whatever logs
that channel. And the error model requires the audit record to carry the problem `detail`, while
`detail` is explicitly permitted to carry sensitive occurrence text — so a refusal written
carelessly writes the secret into the audit store too, which retains for years by design.

## Decision

**UDLM fixes the invariant; policy and profile own the mechanism.** The peer test (ADR-008) settles
where the line falls: two conformant implementations could satisfy this by scanning or by coercing and
both be correct, so the *mechanism* is not UDLM's to choose — the *guarantee* is.

**The UDLM invariant** (`CPX-013`/`CPX-014`, restated, not new): inline credential material submitted
where a reference is required is detected and refused; the detection is **ordered before** the intent
is persisted; and the rejecting path persists neither the material nor an echo of it (in the store, the
error payload, or the audit `detail`). Every conformant implementation must meet this. Ordering is part of
the invariant, not an implementation detail — a correct decision taken *after* the write is a failed
decision, because the store is immutable.

**Delegated to policy/profile (a DCM obligation).** *How* intake meets the invariant — and *how strictly*
— is a policy decision the implementation makes, and its rigor is a **profile floor**:

- A profile may accept **detect-and-refuse-before-persist** (mechanism A below) as the floor, or **raise
  the floor to coercion-to-a-reference** (mechanism D) where the stakes warrant — the same profile-priced
  rigor as bare-vs-governed vocabulary (ADR-007). UDLM names the *knob*; the profile sets it.
- The implementation (DCM) picks the mechanism that satisfies the invariant at its profile's floor.

UDLM does **not** rule scan-vs-coerce-vs-quarantine. The catalogue that follows is informative — the
shapes an implementation may implement and their honest costs, recorded so DCM's policy work weighs them
rather than rediscovering them. **This is registered as a DCM policy item** (see *Delegated work* below).

### Mechanism A — Scan before persist *(the common floor)*

Intake runs the credential-material check on the submitted body before any write, and a positive
result short-circuits: nothing is stored, the typed refusal is returned, and the audit record
carries the field path and the violation class.

*Why it is the floor:* it is the only shape that is correct without adding a store. It follows
directly from the immutability constraint rather than working around it, it needs no new artifact
and no new lifecycle, and it reuses detection logic the model already specifies elsewhere
(known credential formats, private-key and certificate blocks, entropy heuristics on
reference-typed fields), applied at a new point rather than invented.

*Its costs, stated honestly:* the check is on the synchronous intake path, so its cost is paid by
every request, including the overwhelming majority that carry no secret. Entropy heuristics
produce false positives — a legitimately random identifier in a reference field can be refused —
and the remedy for a false positive on this path is unpleasant, because the submitter must alter
a value they believe is correct. And scanning is heuristic by nature: a secret in a format the
scanner does not recognize passes, so the check reduces exposure rather than eliminating it.
Presenting it as a guarantee would be dishonest; it is a strong default with a known ceiling.

### Mechanism B — Quarantine buffer

The intent is written first, to a short-lived quarantine store that is *not* the Intent store —
mutable, retention-bounded, permitted to delete — and promoted into the Intent store only after
it passes. Refused bodies age out of quarantine and never reach the immutable store.

*What it buys:* the check comes off the synchronous path, and asynchronous or heavier analysis
becomes possible. A refused submission remains inspectable for a bounded window, which has real
diagnostic value.

*Its costs:* it introduces a second store holding raw consumer submissions, which is to say a new
place secrets can be, with its own access control, its own retention, its own backups, and its own
breach surface. It also creates a state that the four-state model does not have: a submission that
is neither Intent nor rejected. Every consumer of "what was asked for" now has to know about a
pre-Intent stage. The mechanism reduces the *duration* of exposure and increases the *number of
places* exposure can occur, which is a poor trade for a value that must not be stored at all.

### Mechanism C — Provider-side redaction

Persist the intent as submitted, and rely on redaction at every read: the state store holds the
literal, and readers receive a masked view.

*What it buys:* no change to the intake path, and no risk of refusing a valid request.

*Its costs:* it does not satisfy the requirement — the secret *is* stored, in the append-only
store, forever, and masking on read is a display property that any operator with store access,
any backup, and any replica bypasses. It also inverts the model's own posture, which is that
values do not enter the implementation's stores at all rather than entering and being hidden. Listed
because it is the shape a team reaches for when the immutability constraint is discovered late,
and it should be explicitly rejected rather than silently available.

### Mechanism D — Intake-time coercion to a reference *(a profile may require this)*

Rather than only judging the submitted value, intake *transforms* it: the literal is handed to the
credential provider, which stores it and returns a reference; the intent that is persisted carries
the reference, and the submitter is told what happened. The precedent is in the model already —
the vocabulary-intake ladder resolves a submitted free string against the vocabulary and, where no
match exists and the profile permits, mints a new element and binds the submission to it. Match or
mint, at intake, so that the stored artifact is well-formed even when the submission was not. This
is the same move applied to credential material: the submission is repaired into the shape the
model requires instead of being bounced.

*What it buys:* the strongest end state. The consumer's mistake produces a correct artifact, the
secret ends up in the one place designed to hold it, and the ergonomics are those of a system that
helps rather than scolds — which matters, because a refusal loop teaches submitters to work around
the check.

*Its costs, which are the reason it is not the floor:* coercion means the substrate briefly handles
a credential value on the intent path, and that is precisely what `CPX-001` exists to prevent. It
would need a narrow, explicitly-scoped exception — hand-off only, never at rest, never logged —
and such exceptions are how value-separation disciplines erode. It also silently changes what a
submitter asked for, which the ladder makes acceptable only because minting is profile-gated and
recorded; the same gating and recording would be required here. And it presumes an issuing
provider is reachable and authorized at intake, which is a new availability dependency on the
request path. Hence: available where a profile chooses to price it, never the default, and never
the mechanism a conformance floor assumes.

### The audit-content question, settled either way

Whichever mechanism is chosen, the error model's requirement that an audit record carry the
problem `detail` — where `detail` may carry sensitive occurrence text — resolves in one direction
on this path: the emitter does not put the refused material in `detail`, so the record cannot
inherit it. The audit record names the field path and the violation class. This is the hash-only
leaf discipline the audit model already applies to field values, extended to the error path that
feeds it, and it is stated in `contracts/error-model.md` §6a rather than here so it applies to
every refusal rather than only this one.

## Delegated work — the DCM policy obligation

Registered in the DCM policy-obligations register. **DCM must** decide and implement, as a policy
governed by the profile:
- **the mechanism** (a Mechanism above, or another that satisfies the invariant): where the check sits in
  the intake pipeline, the detector (formats, entropy thresholds, tuning), and its false-positive remedy —
  most plausibly a per-field opt-out declared on the type, itself reviewable;
- **the profile floor**: which profiles accept detect-and-refuse (A) and which require coercion-to-a-
  reference (D). Under coercion, DCM must record the transformation and its provenance (the vocabulary-
  ladder discipline), and price the narrow `CPX-001` exception (hand-off only, never at rest, never logged).

UDLM will not accept a UC or conformance claim that asserts a *specific* mechanism as the portable
requirement; the portable requirement is the invariant. The mechanism belongs to DCM.

## Data · Policy · Provider

- **Data** — the Intent record's immutability is the constraint that makes this a design question:
  the model's own guarantee about what was asked for is what forbids a cleanup path. The
  credential reference type is the destination shape.
- **Policy** — the detection-and-refusal decision, its ordering relative to persistence, and (under
  Option D) whether coercion is permitted at this profile. Ordering is a policy property here, not
  an implementation detail: a correct decision taken after the write is a failed decision.
- **Provider** — the credential provider holds values and issues references; under Option D it is
  on the intake path, which is the new dependency that option introduces. No realizing provider is
  dispatched for a refused intent.

## UDLM vs DCM — what lands where (the peer test, ADR-008)

| Piece | **UDLM** — model / contract (a peer MUST honor) | **DCM** — engine / mechanism (a peer MAY differ) |
|---|---|---|
| The prohibition | inline credential material where a reference is required is invalid (`CPX-013`) | — |
| Ordering | the check precedes persistence — a normative sequencing constraint | where in the intake pipeline the stage sits |
| The refusal | typed code, named field, named remediation, non-persistence (`CPX-014`) | the emitting service, the message text |
| Detection | *that* submitted values are checked | the detector: formats, entropy thresholds, tuning |
| Coercion (Option D) | that a coerced intent records the transformation and its provenance | the issuing call, retries, availability handling |

**A fifth shape, considered and set aside — persist-with-redaction:** write the Intent with
the offending field replaced by a marker + hash, preserving an immutable record of the refused
ask without the secret. It buys forensic continuity (under Option A a refused submission
leaves only its REFUSE audit record) at the cost of a mutation-on-intake precedent the
append-only store otherwise never makes. Not clearly better than A; recorded so the
engineering pass weighs it rather than rediscovering it.

## Consequences

- Intake gains a stage that inspects submitted *values*, not just their shapes. That is a genuine
  addition to what intake does, and the false-positive path needs a named remedy before this
  ships — most plausibly a per-field opt-out declared on the type, which is itself reviewable.
- The must-reject case's non-persistence criterion becomes satisfiable. It is not satisfiable
  today under any reading of the written model, which is the finding that produced this ADR.
- Choosing Option D later, after Option A ships, is cheap: the detector is the same, and coercion
  replaces the refusal at the same point in the pipeline. Choosing Option B later is not cheap —
  it changes where raw submissions live. That asymmetry is a reason to start at A.
- A ruling here also settles the smaller sibling question the corpus keeps hitting: whether error
  payloads may echo submitted values. They may not, and the general rule lives in the error model
  so that no surface has to re-decide it.

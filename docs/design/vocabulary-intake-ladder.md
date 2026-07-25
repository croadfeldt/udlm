# The vocabulary-intake ladder — match, mint, promote, under profile control

**What this settles:** how plain string parameters and SharedDataElements coexist without
forcing vocabulary mechanics on authors who gain nothing from them — the north star (removal
of toil through enablement) applied to the reference discipline itself. The strict rule
(PVD-001: reference, codelist, or requirement — never a free string) stays the destination;
this ladder is how strings *get there* at a cost proportional to the governance each estate
actually wants. UDLM defines the contract — the element store, scope visibility, the
proposed→canonical status ladder, and the matching rules; **DCM executes it at intake**, as
admission-time matching (validation) and minting (transformation enrichment). Contracts are
proposed pending ruling; the corpus family (`use-cases/vocabulary-intake/`, six cases) encodes
them for measurement first.

## The ladder, in plain terms

An author types a string. Three things can happen, and the estate's profile decides which are
available:

1. **Match** — the string exactly (after normalization) matches a SharedDataElement visible in
   the author's scope: it binds automatically and becomes a governed reference. The author
   paid nothing and got vocabulary discipline free. This verb is available in *every* profile
   — strictness gates minting, never matching. **Near matches never bind silently**: a synonym
   or variant is surfaced as a candidate the author (or a curator) decides on — silent
   approximation is how vocabularies rot and counts silently corrupt.
2. **Mint** — no match, and the profile permits it: a new SharedDataElement is created at the
   author's **current (narrowest) scope**, status `proposed`, carrying minted-from provenance
   (the string, the author, the intent that carried it). The request proceeds uninterrupted.
   Vocabulary is **harvested from usage** instead of demanded before it.
3. **Promote** — a proposed element that earns adoption is promoted to canonical — and
   optionally up a scope tier — through the standard element-promotion operation, with
   **deduplication at promotion time** (near-duplicates merge, references re-bind) rather than
   at mint time: curation cost lands where the decision is made, not where the string was
   typed. Scope promotion is the class system's portability-improvement operation — a casual
   string can end its life as a Base-tier element every provider shares.

## The profile ladder (defaults — advisory, per the north star)

| Profile | Intake mode | Unknown string |
|---|---|---|
| homelab / dev | mint-on-write | mints, proposed, uninterrupted |
| standard | mint-with-review | mints proposed + queues for curation |
| prod | match-only | typed refusal naming nearest candidates + the proposal path |
| fsi / sovereign | canonical-only | refusal; vocabulary extension runs through the estate's own change control, and interim refusals cite the pending proposal |

These are defaults an estate adopts by reference or overrides by declaring its own intake
policy — the response-matrix discipline applied to vocabulary. The toil accounting is the
design's justification: match removes toil everywhere; mint defers curation until an element
proves it deserves any; strict modes spend author toil only where the estate has decided
governance is worth it.

## What this asks of the model (the ruling surface)

The element store, scoped visibility, and promotion already belong to the class realization
(P0/P1). Genuinely new and needing a ruling: the `proposed | canonical` status on
SharedDataElements with minted-from provenance; the intake-mode policy vocabulary
(mint-on-write / mint-with-review / match-only / canonical-only); the exact-only auto-bind
rule with candidate-surfacing semantics; and promotion-time dedup with reference re-binding.
The DCM half — where in admission the match/mint runs and how enrichment records the binding —
follows the existing validation/transformation policy split.

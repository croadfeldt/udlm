# UDLM 1.0 — Lockdown plan

**Normative** — how UDLM gets from `udlm/0.1` to the `udlm/1.0` tag (register row 127).
**What this settles:** what 1.0 promises, what has to change before the tag because it would
cost a 2.0 afterwards, what waits for 1.x because it only adds, and the order the work lands in.
It replaces the exit criteria in [`UDLM-0.1-SCOPE.md`](UDLM-0.1-SCOPE.md) §5.

## 1. Three rulings (maintainer, 2026-10-28)

1. **The maintainer cuts 1.0.** In July, 1.0 was to be conferred by an engineering review (#217).
   Since then the register has accepted 47 of 49 ADRs one row at a time, and the estate has used
   the model end to end (rows 082–125). That is the review. #217 closes when 1.0 is tagged.
2. **The conformance suite is the existing checks, packaged.** The record checks in `tests/` and
   the examples in `registry/examples/` become suite `1.0.0`: one command anyone can run against
   their own records, versioned with the spec, named in `CONFORMANCE.md` §8. The HTTP-level
   checklist (§6) comes in 1.x; a 1.0 declaration says so. The estate's records are the first run.
3. **Class versions stay as they are** (#645). `conforms_to` says which spec a record follows;
   `version` says which revision of the class. A class version only means something inside its
   spec major, so `Machine 2.4.1` promises the same under `udlm/1.0` as it did under `0.1`.
   `VERSIONING.md` gets one sentence saying so. No `type_ref`, pin or estate record changes.

## 2. What 1.0 promises

From the tag, any two implementations on the same spec major can exchange records
(`VERSIONING.md`, `CONFORMANCE.md` §9). To keep that true:

- Record schemas (`state-record`, `entity-view`, `composition-record`, `decision-record`, audit
  and ledger records) and `common-elements` only gain things; nothing is removed or renamed.
- The class grammar (`class.schema.json`), the served specs under `registry/generated/` and the
  three class tiers (ADR-082) only gain things. A breaking change to one class is that class's
  own major bump.
- Every rule ID in `rule-id-registry.yaml` keeps its meaning. A rule is retired by deprecation,
  never by editing it in place.
- The integrity chain (`sha256_jcs`; `sha256-jcs` still reads as history, row 121) and the
  identifier scheme (v7 record ids, v4 entity ids) do not change.
- Breaking any of these means `udlm/2.0`.

Not promised at 1.0: the HTTP binding (§6), the profile set (moving out, #488), and everything
in §4.2.

## 3. The freeze

From the day this document merges:

- Nothing new lands in 0.1 except the blockers in §4.1. A new idea becomes an issue labelled
  `1.x` and waits.
- A blocker is anything that would be a breaking change after the tag: a rename; a field removed,
  narrowed or made required; a closed list of values that is not settled; a wrong default; a rule
  the spec states that no schema carries; a decision the spec claims that nothing implements.
- Adding things (an optional field, a class, an edge, an output) is never a blocker. Adding is no
  harder after 1.0, so it waits.
- Until the tag, breaking changes still take a minor bump (the pre-1.0 rule). That rule ends at
  the tag.
- Additive work raised during the freeze goes up as a draft PR that says it is waiting on this
  section, until the maintainer rules on it (first case: volume replication, #689).

## 4. The open issues (90 on 2026-10-28), sorted

One decision per kind of problem, the way the field sweep worked (row 108). Each row says why.

### 4.1 Blockers — must land before the tag

| # | Problem | Why it cannot wait | Package |
|---|---|---|---|
| #641 | 36 enum values are not snake_case | renaming later is breaking; adopted code lists keep their spelling and say so | WP1 |
| #678 | the decision-record ladder is uppercase; composition and curation_state are not | one ladder with two spellings; renaming later is breaking | WP1 |
| #472 | `sovereignty.classification` is free text with no list of values | adding a closed list later narrows the field | WP1 |
| #346 | the request status ladder is not settled | a closed list cannot grow later without a major bump | WP1 |
| #410 | two isolation vocabularies that do not match, neither recordable | settle on one before it is frozen | WP1 |
| #466 | the rehydration policy has four values and nowhere to record them | a list with no field cannot be promised | WP1 |
| #351 | rebuild lineage: RHY-005 names fields no schema has | a rule no schema carries cannot be certified | WP2 |
| #352 | reduction disclosure: the portable element (listing the paths waits for 1.x) | same | WP2 |
| #353 | zero-output classes are exempted by a hand-kept list, not a marker in the schema | the marker changes the grammar; add it before the grammar freezes | WP2 |
| #559 | fill strategy (`auto`, `prompt`, `auto_with_override`) is documented but has no field | give it a field or delete the text | WP2 |
| #562 | `cohesion: same_zone` exists and nothing refuses a violation | add a check or remove the element; removing later is breaking | WP2 |
| #445 | two of six identifier rules do not hold (WIR-003 is unenforced; one describes a removed design) | adding a pattern later narrows the field; confirm `$defs/handle` covers WIR-003, drop the dead one | WP2 |
| #412 | `component_id` has no scope, so nested templates collide | scoping a key later is breaking | WP2 |
| #415 | `ownership_model` is declared on 9 of 71 classes | declare it everywhere or never require it; requiring it later is breaking | WP2 |
| #469 | StorageVolume is listed under two ownership models | the contradiction behind #415 | WP2 |
| #406 | cross-tenant grants have no use limit and default to never expiring | changing a default is breaking | WP2 |
| #189 | `reference_data` is still a `layer_type`; `applies_on` and `from_layers` are not built (ADR-038) | removing an enum value is breaking | WP2 |
| #634 | provider registration has no schema (115 of 173 keys in the contract) | a contract with no schema cannot be in a 1.0 claim | WP3 |
| #632 | entity-relationships describes fields no schema has; four rules depend on them | model each field or move the text to the control plane | WP3 |
| #614 | every network class declares zone and tier, even where they do not apply | removing fields is breaking | WP4 |
| #612 | ADR-082 follow-ups | the udlm side is done; what remains is estate work; close here | WP4 |
| #646 | LogShipper names OpenTelemetry but adopts nothing; KubernetesNodePool adopts nothing | the standards register must be true at the tag | WP4 |
| #488 | the six profiles are not UDLM's | 1.0 cannot ship one implementation's profiles; move them to `udlm-profiles` | WP5 |
| #489 | per-profile values are spread over 10 documents and 55 rows | the same move | WP5 |
| #490 | two picked numbers (request groups capped at 50, auto-approve score capped at 50) | a local decision shipped as a rule would have to be kept | WP5 |
| #503 | the spec names an implementation (57 lines in 21 files left, from 482) | "independent of any implementation" has to be true at the tag | WP6 |
| #491 | a dot means three things and the spec says two | a grammar statement; it already caused one wrong design | WP6 |
| #416 | 319 MUST against 9 SHOULD | partial conformance (§3.2) means nothing without levels | WP6 |
| #460 | template-composition-model: about 60 lines to cut, 37 belong to the control plane | text about a construct the model moved past | WP6 |
| #428 | ADR-059's record test has no written reason | the rule exists; a reader needs the why | WP6 |
| #382 | reference aliases: the rule for resolving an unpinned name was never written | a resolution rule added later changes behaviour | WP6 |
| #328 | identity is not address | one paragraph: UDLM never says how a provider reaches a thing | WP6 |
| #392 | does the assembly engine own its own conditions, as the policy engine does (ADR-065)? | a cheap ruling; leaving it open freezes the ambiguity | WP6 |
| #401 | does the model carry GUI layout? | ruling: no; close | WP6 |
| #417 / #442 / #434 | no conformance suite exists; must-reject covers 24 cases | ruling 2: package the checks and examples as suite 1.0.0; give every checked rule a must-reject case | WP7 |
| #383 | the reference lint has two blind spots | a suite with known blind spots is not a 1.0 suite | WP7 |
| #424 | nothing checks the merged result | a required check on `main` or a merge queue; two green branches once made a red main | WP7 |
| #645 | class versions overstate stability | ruling 3: keep them; one sentence in `VERSIONING.md` | WP8 |
| #394 | ADR-059's typed chains have no schema | build them or narrow the ADR; an accepted ADR with nothing behind it cannot stand at the tag | WP8 |
| #407 | ADR-066 A–E: the tenant boundary is operational | the same test | WP8 |
| #385 | the residency rule in §3.8 cannot be evaluated (ISO 3166 vs `sovereignty.zone`) | a rule that cannot be evaluated is fixed or dropped, not frozen | WP8 |
| #321 | the control plane flattens the class graph; UDLM's generator is the reference | ruling made; confirm the spec says it, close | WP8 |
| #474 / #477 | a catalog item is a provider class; retire the record kind; catalog metadata has no home | renames are breaking; `composition.schema.json` still names `catalog_item` | WP8 |
| #217 | ratification pass | closes with the tag (ruling 1) | WP9 |

### 4.2 1.x — only adds, waits for the tag

New classes, optional fields, outputs, edges and capabilities. Each is a minor bump after 1.0 and
loses nothing by waiting:

- Operations: #330 start and stop as processes, #331 freeze, #332 notifications, #333 runtime
  role, #336 operational health, #334 enablement chains, #338 operational data model, #337 shape
  layer with reconvergence, #59 setpoints.
- Intent and composition: #224 true intent, #335 consumer-authored composition, #481 constituent
  counts, #324 cross-element constraints, #325 shared elements across a provider family, #409
  checking that the pieces of one thing landed together.
- Network: #350 NetworkRoute, #500 and #501 VPC, #199 portable isolation intent, #384 where
  control-plane components may run.
- Storage and compute: #250 DR pairing, #251 FileShare outputs, #241 vCPU ceiling, #242 CPU
  mode, #243 day-0 access, #244 thin provisioning, #615 vendor BIOS provider class, #613 type
  tiers on demand.
- Knowledge: #190 `runs_image`, #188 third-party SBOM system of record, #195 FSI flow rewrite,
  #197 knowledge records as proof of concept.
- Tooling and adoption: #222 SDK, #326 authoring scaffolding, #341 provider class library, #343
  cross-provider adoption, #486 CI check for local decisions dressed as rules, #553 synthetic
  estate.
- Conformance, second half: the HTTP-level runner (§6).

### 4.3 Closed by this plan or by checks that already run

- #194 and #198 (is every stored field derivable? is it used?): the field sweep (rows 100–119,
  #664) asked both of every element; row 108 is the standing rule. Close.
- #567 and #623 (monthly cleanliness reviews): the checks run on every change; the freeze makes
  the review redundant. Close.
- #327 (edges have no state): row 078 put observed edges on the discovered record; comparing
  declared with observed edges is the drift check. Close with a pointer.

## 5. Work packages and order

Each package is one PR of at most 3k lines: spec first, every derived file in the same PR, one
register row. Order is by what unblocks what; WP1–WP6 can run in parallel. Owners on 2026-10-28:
the estate session has WP4, WP7, WP3 in that order; the udlm session has WP1, WP2, WP5, WP6,
WP8, WP9.

| Package | What it does | Closes |
|---|---|---|
| WP1 vocabulary | fixes casing and settles the four open lists of values | #641 #678 #472 #346 #410 #466 |
| WP2 schema homes | every field the spec mentions gets a schema, or the mention goes | #351 #352 #353 #559 #562 #445 #412 #415 #469 #406 #189 |
| WP3 provider contract | a provider-registration schema; entity-relationships matched to the schema | #634 #632 |
| WP4 ADR-082 closeout | prune zone and tier from network classes; fill the adopts gaps | #614 #612 #646 |
| WP5 profiles out | move the profiles and per-profile values to `udlm-profiles`; remove the picked numbers | #488 #489 #490 |
| WP6 spec text | remove implementation names, state the dot grammar, audit MUST/SHOULD, cut stale text, four short rulings | #503 #491 #416 #460 #428 #382 #328 #392 #401 |
| WP7 conformance | suite 1.0.0: a runner that takes a record tree, a must-reject case for every checked rule, the lint blind spots, a merge check | #417 #442 #434 #383 #424 |
| WP8 built as decided | every accepted ADR is built, superseded or narrowed; the catalog-item retirement finished | #645 #394 #407 #385 #321 #474 #477 |
| WP9 the tag | the procedure in `VERSIONING.md`: re-stamp `conforms_to` and `$id`, the meta-schema `$id`, `CONFORMANCE.md` from Draft to binding, tag `udlm/1.0` | #217 |

## 6. Exit criteria

The tag is cut when all of these hold. `tests/check_status_claims.py` checks this document
against them.

1. Every issue in §4.1 is closed, or moved to another bin by a register row.
2. `check_adr_realization` finds no accepted ADR with nothing built behind it.
3. The suite runner passes against the estate's records, and `CONFORMANCE.md` §8 names suite
   `1.0.0` without "under construction".
4. The profiles are out of the repo, and `conforms_to: udlm/1.0` is the only spec version in
   `registry/`.
5. Every validate.yml step passes on the tagged commit.

# UDLM 1.0 — Lockdown plan

**Normative** — the committed path from `udlm/0.1` to the `udlm/1.0` tag (register row 126).
**What this settles:** what 1.0 promises, what must change before the cut because it would cost a
2.0 afterwards, what waits for 1.x because it only adds, and the order the work lands in. It
succeeds [`UDLM-0.1-SCOPE.md`](UDLM-0.1-SCOPE.md) §5, whose exit criteria it replaces.

## 1. Three rulings (maintainer, 2026-10-28)

1. **The maintainer cuts 1.0.** The July ruling made 1.0 something engineering acceptance confers
   (#217). Since then the register ratified 47 of 49 ADRs row by row, and the estate has consumed the
   model end to end as its proving ground (ADR-082 onward, rows 082–125). That is the acceptance;
   #217 closes with the cut. `VERSIONING.md` "Who confers 1.0" is amended.
2. **The conformance bar is the gates and the corpus, packaged.** The record-level gates in `tests/`
   and the corpus in `registry/examples/` become conformance suite `1.0.0`: one command a peer runs
   against a tree of its own records, versioned with the spec, declared in `CONFORMANCE.md` §8 and
   written into `conformance_test_suite_version`. The wire-level checklist (§6: HTTP paths, retries,
   rate limits) stays a 1.x deliverable and is declared as such; a 1.0 declaration covers the record
   contracts. The estate's records at home are the first run.
3. **Class versions do not re-baseline** (#645). The two-axes rule in `VERSIONING.md` already says
   `conforms_to` is the spec axis and `version` is the entity axis; a class version is meaningful
   within its spec major, so `Machine 2.4.1` under `udlm/1.0` promises exactly what it promised under
   `0.1`. One sentence is added to say so. Nothing in a `type_ref`, the pin manifest or an estate
   record moves.

## 2. What 1.0 promises

From the tag, "same spec MAJOR = wire-compatible" binds (`VERSIONING.md`, `CONFORMANCE.md` §9):

- The record schemas (`state-record`, `entity-view`, `composition-record`, `decision-record`, the
  audit and ledger records) and `common-elements` change only additively.
- The class grammar (`class.schema.json`), the served specs under `registry/generated/`, and the
  three-tier class model (ADR-082) change only additively; a class breaking change is that class's
  MAJOR, under the strict post-1.0 regime.
- Every rule ID in `rule-id-registry.yaml` keeps its meaning; a rule is withdrawn by deprecation,
  never by silent edit.
- The integrity chain (`sha256_jcs`, with `sha256-jcs` read as history, row 121) and the identifier
  scheme (v7 record ids, v4 entity ids) are fixed.
- Breaking any of these is `udlm/2.0`.

What 1.0 does **not** promise: the wire-level HTTP binding (§6), the profile set (extracted, #488),
and anything in §4 below.

## 3. The freeze

From the day this document merges:

- No new modeling lands in 0.1 except the blockers in §4. A new idea goes to an issue labelled
  `1.x` and waits.
- A blocker is anything that would be a **breaking change after the cut**: a rename, a removed or
  narrowed field, a closed vocabulary that is not yet settled, a default that is wrong, a rule the
  spec states that no schema carries, a decision the spec claims that no surface realizes.
- Additive work (a new optional field, a new class, a new edge, a new output) is not a blocker. It
  is cheaper after 1.0, not more expensive, so it waits.
- Breaking changes still take a MINOR bump until the tag (the pre-1.0 floor); the floor ends at the
  tag.

## 4. Triage of the open issues (90 as of 2026-10-28)

Ruled once per pattern, the way the field sweep was (row 108). Each row says why it is in its bin.

### 4.1 Blockers — breaking after the cut, or the cut's own gates

| # | What | Why it cannot wait | Work package |
|---|---|---|---|
| #641 | 36 enum values off snake_case; own vocabularies mix styles | a rename is breaking; adopted codelists get `x-standard`, the rest rename | WP1 |
| #678 | decision-record ladder uppercase, composition/curation_state snake_case | one ladder, two spellings; a later rename is breaking | WP1 |
| #472 | `sovereignty.classification` is a free string with no vocabulary | adding a closed vocabulary later is narrowing (MAJOR) | WP1 |
| #346 | request status ladder (submitted → accepted → in-progress → success/failure) unsettled | a closed enum added later cannot be extended without MAJOR | WP1 |
| #410 | two isolation vocabularies that never meet, neither recordable | the vocabulary must be one before it is frozen | WP1 |
| #466 | rehydration provider-selection policy has four values and no home | a vocabulary with no home cannot be promised | WP1 |
| #351 | rebuild lineage: RHY-005 names fields no schema carries | a rule the schema does not carry is a rule 1.0 cannot certify | WP2 |
| #352 | reduction disclosure: the portable element (the path half stays 1.x) | same | WP2 |
| #353 | output-exemption marker on the meta-schema, not a hand list | the gate binds by hand list; a marker added later changes the grammar | WP2 |
| #559 | fill strategy (`auto`/`prompt`/`auto_with_override`) documented, carried nowhere | home it or delete the prose; prose with no field is a false promise | WP2 |
| #562 | `cohesion: same_zone` ships and nothing refuses a violation | a gate or removal; a shipped element nobody checks is a 2.0 removal later | WP2 |
| #445 | two of six identifier requirements do not hold (WIR-003 unenforced, one describes a removed design) | a pattern added later is narrowing; verify `$defs/handle` closes WIR-003, drop the dead one | WP2 |
| #412 | `component_id` has no namespace; nested templates collide | scoping a key later is breaking | WP2 |
| #415 | `ownership_model` declared on 9 of 71 classes | declare on all or make it never-required; making it required later is MAJOR | WP2 |
| #469 | StorageVolume listed under two ownership models | doc contradiction behind #415 | WP2 |
| #406 | cross-tenant grants: no use bound, `expires_at: null` default | changing a default is breaking | WP2 |
| #189 | `reference_data` still in `layer_type`; `applies_on`/`from_layers` unrealized (ADR-038) | removing an enum value is breaking | WP2 |
| #634 | provider registration has no schema (115 of 173 contract keys) | a wire contract with no schema cannot be in a 1.0 conformance claim | WP3 |
| #632 | entity-relationships describes fields no schema carries; four rules depend on them | model each or move the prose to the control plane | WP3 |
| #614 | every network Base declares zone and tier; prune where the Base cannot carry them | removing fields is breaking | WP4 |
| #612 | ADR-082 follow-ups | udlm side done; the remaining box is estate work; close here | WP4 |
| #646 | LogShipper names OpenTelemetry but adopts nothing; KubernetesNodePool adopts nothing | the standards register must be true at the tag | WP4 |
| #488 | the six profiles are not UDLM's | 1.0 cannot ship one implementation's profiles as spec surface; extract to `udlm-profiles` | WP5 |
| #489 | per-profile values scattered through 10 documents, 55 rows | same extraction | WP5 |
| #490 | picked numbers: request groups capped at 50, auto-approve score capped at 50 | an organizational decision shipped as a rule is a rule 1.0 would have to keep | WP5 |
| #503 | the spec names an implementation (57 lines in 21 files remain of 482) | "independent of any implementation" must be true at the tag | WP6 |
| #491 | a dot means three things and the spec says two | grammar statement; caused one wrong design already | WP6 |
| #416 | 319 MUST : 9 SHOULD | partial conformance (§3.2) means nothing without levels; audit before levels freeze | WP6 |
| #460 | template-composition-model: ~60 lines to cut, ~37 belong to the control plane | prose that describes a construct the model moved past | WP6 |
| #428 | ADR-059's record test needs its reason written | the rule exists; the reason is what a 1.0 reader needs | WP6 |
| #382 | reference aliases: the unpinned-resolution rule never written | a resolution rule added later changes behaviour | WP6 |
| #328 | identity is not address | a one-paragraph ruling: UDLM never carries how a provider reaches a thing | WP6 |
| #392 | does the assembly engine own its predicates (ADR-065 for assembly)? | a ruling, cheap; leaving `activation_condition` ambiguous freezes the ambiguity | WP6 |
| #401 | GUI layout in the model? | ruling: no; close | WP6 |
| #417 / #442 / #434 | the conformance suite does not exist; must-reject covers 24 cases | ruling 2 — package the gates and corpus as suite 1.0.0; widen must-reject to every rule a gate binds | WP7 |
| #383 | G3 reference-lint has two coverage holes | a suite with known holes is not a 1.0 suite | WP7 |
| #424 | nothing verifies the merge | a required check on `main` or a merge queue; two green branches made a red main once | WP7 |
| #645 | class versions overclaim stability | ruling 3 — keep; one sentence in `VERSIONING.md` | WP8 |
| #394 | ADR-059's typed chains have no schema surface | realize or narrow the ADR; an Accepted ADR with no surface cannot stand at the tag | WP8 |
| #407 | ADR-066 A–E: tenant boundary is operational | same test | WP8 |
| #385 | §3.8 residency-subsumption cannot be evaluated (ISO 3166 vs `sovereignty.zone`) | a rule that cannot be evaluated is dropped or fixed, not frozen | WP8 |
| #321 | the control plane flattens the class graph; UDLM's generator is the reference | ruling recorded; verify the spec says it, close | WP8 |
| #474 / #477 | catalog item is a provider class; retire the record kind; catalog metadata has no home | renames are breaking; `composition.schema.json` still references `catalog_item` | WP8 |
| #217 | ratification pass | closes with the cut (ruling 1) | WP9 |

### 4.2 1.x — additive, waits for the tag

New classes, optional fields, outputs, edges and capabilities. Each lands as a MINOR bump after
1.0 and costs nothing by waiting:

- Operations family: #330 start/stop processes, #331 freeze, #332 notifications, #333 runtime role,
  #336 operational health, #334 enablement chains, #338 operational data model, #337 shape layer
  with reconvergence, #59 setpoints.
- Intent and composition: #224 true intent, #335 consumer-authored composition, #481 constituent
  cardinality, #324 cross-element constraints, #325 provider-family element sharing, #409 placement
  compatibility of a thing's pieces.
- Network: #350 NetworkRoute, #500/#501 VPC, #199 portable isolation intent, #384 control-plane
  placement.
- Storage and compute probes: #250 DR pairing, #251 FileShare outputs, #241 vCPU ceiling, #242 CPU
  mode, #243 day-0 access, #244 thin provisioning, #615 vendor BIOS Provider Class, #613 Type tiers
  on demand.
- Knowledge: #190 `runs_image`, #188 third-party SBOM system of record, #195 FSI flow rewrite,
  #197 Knowledge records as POC.
- Tooling and adoption: #222 SDK, #326 authoring scaffolding, #341 Provider Class library, #343
  cross-provider adoption, #486 CI shape detector for organizational decisions, #553 synthetic
  estate.
- Conformance, second half: the §6 wire-level runner.

### 4.3 Closed by the lockdown or by standing gates

- #194 derive-candidacy and #198 unused-data: the field sweep (rows 100–119, #664) applied both
  tests to every element; the standing law is row 108. Close.
- #567, #623 monthly cleanliness reviews: superseded by the freeze; the gates run on every change.
- #327 edges have no state dimension: closed by row 078 (observed edges ride the discovered record)
  and RHY-007; drift between declared and observed edges is the comparison. Close with a pointer.

## 5. Work packages and order

Each is one PR of ≤3k lines, spec first, every derived surface in the same PR, a register row.
Order is by what unblocks what; WP1–WP6 can run in parallel across sessions.

| WP | Carries | Closes |
|---|---|---|
| WP1 vocabulary | casing and the four unsettled vocabularies | #641 #678 #472 #346 #410 #466 |
| WP2 schema homes | every stated field gets a schema or the statement goes | #351 #352 #353 #559 #562 #445 #412 #415 #469 #406 #189 |
| WP3 provider contract | provider-registration schema; entity-relationships reconciled | #634 #632 |
| WP4 ADR-082 closeout | network zone/tier prune; adopts holes | #614 #612 #646 |
| WP5 profiles out | profiles and per-profile values to `udlm-profiles`; picked numbers removed | #488 #489 #490 |
| WP6 spec text | implementation names, dot grammar, MUST/SHOULD, audits, the four cheap rulings | #503 #491 #416 #460 #428 #382 #328 #392 #401 |
| WP7 conformance | suite 1.0.0: `tests/conformance.py <record-tree>`, must-reject widened, G3 holes, merge check | #417 #442 #434 #383 #424 |
| WP8 realization | every Accepted ADR realized, superseded or narrowed; catalog-item retirement finished | #645 #394 #407 #385 #321 #474 #477 |
| WP9 the cut | `VERSIONING.md` procedure: re-stamp `conforms_to` and `$id`, meta-schema `$id`, `CONFORMANCE.md` Draft → binding, tag `udlm/1.0` | #217 |

## 6. Exit criteria

The tag is cut when all of these are true, and `tests/check_status_claims.py` holds this document
to them:

1. Every §4.1 issue is closed or re-binned by a register row.
2. `check_adr_realization` reports no Accepted record without a surface.
3. `tests/conformance.py` runs against the estate's record tree and passes; `CONFORMANCE.md` §8
   names suite `1.0.0` and no longer says "under construction".
4. The profile set is out of the repo and `conforms_to: udlm/1.0` is the only spec version in
   `registry/`.
5. Every validate.yml step passes on the commit that is tagged.

# Blueprint: keeping software supply-chain records current

**What this settles:** how an organization keeps its software records true over time, so that
"which of our assets does this advisory reach" is answered from records and the answer can be
trusted. The records are the bills of materials, packages, advisories and exploitability statements
of [knowledge-family §4.6](../spec/foundations/knowledge-family.md). This is a process blueprint and
it is non-normative. It adds no rule: every check below reads a field the model already carries, and
the last section lists what the model does not carry yet. Which scanner, which feed and which
scheduler run it are the organization's choice.

## 1. Why this is the work

A record is a claim about a moment. An impact answer walks five kinds of record, and each goes out
of date for its own reason and at its own pace:

| Record | Goes out of date when | Typical pace |
|---|---|---|
| The running thing (`Container`, `Machine`, a device) | something is deployed, updated or replaced | minutes to days |
| `SoftwareBillOfMaterials` | its subject changed after the document was produced | as often as the subject |
| `SoftwarePackage` → `Vulnerability` matches | an advisory is published or its affected range is revised | daily |
| `VexStatement` | the supplier revises its status, or the evidence it rests on is superseded | weeks |
| A thing with no record at all | it was never observed | until someone looks |

The last row matters most. A stale record gives an old answer; a missing record gives no answer and
no warning. So the first duty of the process is to know what it cannot see.

## 2. The loop

Five steps, run continuously. Each is stated as what the record carries (Data), who decides (Policy)
and what does the work (Provider).

| Step | Data | Policy | Provider |
|---|---|---|---|
| **1. Observe** | A Discovered record per subject and per bill of materials, each stamped with `at`, `time_source` and `provider`; edges name targets by natural key (`oci_digest`, `purl`, `vulnerability_id`) | How often each kind of subject is observed | A discovery probe; a scanner or the supplier's published document; the advisory publisher's feed |
| **2. Declare the rhythm** | `expected_observation` on the record: a `cadence` or a `window`, and what being overdue means (`on_exceeded`) | The cadence per kind of subject, and where overdue is normal | none; this is a declaration |
| **3. Judge** | Nothing new is stored. Each verdict in §3 is derived when asked | Which verdicts block a decision and which only inform | Whatever consumer asks: a report, a gate, a graph view |
| **4. Report** | Every answer carries its own currency (§4) | Who is told, and how soon | The reporting or alerting system already in place |
| **5. Close** | A new observation supersedes the old one; a fix is confirmed by a `VexStatement` with `status: fixed` and the `TestEvidence` it rests on | What evidence closes a finding | The same probe and scanner as step 1 |

Step 2 is what keeps the loop honest. Staleness is judged against a declared expectation and never
against one fixed timer (ADR-048: `expected_observation`, verdicts derived and never stored). A
laptop fleet that is offline most of the year and a production registry do not share a clock. Where
nothing is declared, the profile's observation lifetime applies (OBS-005).

## 3. The checks

Each check is a comparison between fields that exist. None needs a stored result.

| # | Check | Compares | A failure means |
|---|---|---|---|
| C1 | **Coverage** | Every `Container` and image-booted `Machine` has a `runs_image` edge to a `SoftwareImage`; every `SoftwareImage`, package-installed `Machine`, cluster and device is the target of a `describes` edge | The asset is invisible to every impact answer. Report it by name |
| C2 | **Resolution** | Every edge on a discovered record resolved its `target_key` to an entity (`target_uuid` present) | The scanner saw something the estate has no record of, or the keys disagree |
| C3 | **Subject match** | The bill of materials' `created_at` against its subject's latest observed change | The document describes a subject that no longer exists in that form |
| C4 | **Rhythm** | Each record's latest `at` against its `expected_observation` | `stale_deviant`: an observation that should have arrived did not. `stale_expected` is healthy |
| C5 | **Feed currency** | The latest `at` across `Vulnerability` records from a feed against that feed's declared cadence | New advisories are not reaching the records. Every answer is suspect until it recovers |
| C6 | **Agreement** | Two `SoftwareBillOfMaterials` records about one subject, from different producers | One producer misses components. The difference is the finding |
| C7 | **Closure** | A subject fixed for an advisory no longer reaches it through a current bill of materials, or carries a `VexStatement` that says `fixed` | The fix was recorded but not observed |

Two properties of the model do part of this work:

- **An image never drifts from its bill of materials.** A `SoftwareImage` is identified by digest, so
  C3 cannot fail for an image. What changes is which image a container runs, and that is the
  `runs_image` edge on the container's next observation.
- **A machine does drift.** A host whose packages are updated in place changes under its bill of
  materials. Its probe therefore produces the document and observes the machine in the same run, and
  C3 compares the two.

## 4. Every answer states its own currency

An impact answer is a derived view, and it is only as current as the oldest record it walked. It
therefore reports three things beside its result:

1. **As of.** The oldest observation the answer relied on.
2. **Not judged.** The subjects C1 to C4 exclude, by name and by reason: no bill of materials, a
   stale one, an unresolved edge. These are neither affected nor clear. They are unknown.
3. **Feed as of.** The currency of the advisory data (C5).

An answer without these reads as complete when it is not. The rule for acting on one follows
ADR-048: a gate that decides on outdated knowledge refuses, because deciding on stale knowledge is
worse than refusing; a display shows the verdict and never refuses.

## 5. Starting cadences

These are starting points an organization tunes by policy, stated here so the first run has
something to judge against.

| Subject | Observe | Why |
|---|---|---|
| Running containers and their images | daily, and on every deploy | deploys are the change event |
| Image bill of materials | once per digest | a digest's contents never change |
| Package-installed machines | daily, and after every update run | updates change the subject in place |
| Clusters, network and management firmware | weekly | releases are infrequent and deliberate |
| Advisory and VEX feeds | daily at least | this is the side that moves without anyone deploying |
| Offline or seasonal fleets | a declared `window` | overdue is normal outside it |

## 6. Measures

Four numbers show whether the process works, each derived from the records:

- **Coverage:** the share of running things C1 passes. The target is all of them; the gap is a list.
- **Age:** the median and the oldest observation among the records an answer uses.
- **Deviant count:** records C4 judges `stale_deviant`. The target is zero, and each one has an owner.
- **Time to answer:** from an advisory's publication to the first impact answer that includes it.

## 7. A worked pass

A storefront service runs one container image on a cluster, on hosts that install packages, behind
a switch.

1. The nightly probe observes the container and its image digest. The digest is new since
   yesterday: a deploy happened. The container's `runs_image` edge now names an image with no
   `describes` edge pointing at it. **C1 fails for one image**, and the report names it.
2. The scanner produces a bill of materials for the new digest. Its record resolves 212 of 214
   `contains` edges; two packages are new to the estate and get records. C1 and C2 pass.
3. The advisory feed publishes a new advisory affecting one package. An impact walk from it reaches
   the storefront image, its container, and two hosts that install the same package.
4. The answer reports: as of last night; not judged, one host whose probe has not reported for three
   days against a daily cadence (**C4, `stale_deviant`**); feed as of this morning.
5. The supplier publishes a statement that the image is not affected, because the vulnerable code is
   not in the execute path. A `VexStatement` records it. The image leaves the affected list with the
   reason attached; the two hosts stay.
6. The hosts are updated. The next probe produces new bills of materials that no longer list the
   affected version. **C7 passes** by observation, with no one editing a record.

## 8. What the model does not carry yet

Stated so that an adopter builds these outside the records for now and does not assume them:

- **Freshness of a feed as a declared fact.** ADR-048 reserves a Knowledge-family element for "is
  this record or feed current" (`as_of`, `valid_until`, `refresh_cadence`) and does not build it.
  Until it lands, C5 reads the latest `at` across a feed's records, and the feed's cadence is the
  `expected_observation` on those records.
- **A record for the feed itself.** Nothing models "the advisory source and when it last synced" as
  an entity, so a feed that publishes nothing new and a feed that stopped look alike in the records.
- **When a subject last changed.** C3 needs the subject's latest change. A probe that observes the
  subject and produces its bill of materials in one run satisfies it by construction; a document
  produced separately relies on comparing observation times.

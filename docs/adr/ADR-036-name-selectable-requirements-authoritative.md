# UDLM ADR-036: A governed term denotes a requirements floor — name-selectable, requirements-authoritative

**Status:** Proposed (ruled 2026-07-27; written up 2026-08-10) — **requires engineering ratification**
**Realized by:** `registry/vocabulary-term.schema.json` (`requirements` — the floor a term denotes)
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)

**Background — read first (the cold reader's on-ramp; skip if you have the context).** Each cited once with what it settles.
- **ADR-038** (scoped Classes): a type is defined Base → Type → Provider, and **scope IS portability**. This ADR is what keeps a *value* portable once the shape is.
- **ADR-012 / ADR-039** (reference data, and the vocabulary intake ladder): a governed vocabulary is a versioned, curated reference-data record, with `proposed → canonical` curation. The floors below live on those records.
- **ADR-007** (profile model): posture decides rigor — which is how this ADR scales from a homelab to a sovereign estate without two mechanisms.
- **T5** (adopt by reference) and **T9** (the substrate never translates into a provider's native spec): the two tenets this exists to protect.
- **NDF-001 / rule 41** (UDLM ships no defaults) — a floor is not a default; the distinction is in *Consequences*.

---

## Context

A consumer wants fast storage. Two providers offer it, and they call it different things: one advertises `SSD`, the other `performance`. A third exposes a native class named `gp3-encrypted`.

There are two obvious ways to model that, and both are wrong.

**Let the consumer name the provider's class.** The request stops being portable the moment it is written — it now contains one provider's vocabulary, and moving it means rewriting it. That is T9 inverted: the substrate has translated into a provider's native spec, just with the consumer doing the translating.

**Invent a UDLM-wide enum of quality words.** Now the model has picked what `fast` means for every estate that will ever use it, which is rule 41's defect, and the words still do not mean the same thing to two providers because nothing says what they *require*.

The recurring failure underneath both: **a name that stands for nothing cannot be matched, and a name that stands for a vendor cannot be moved.**

## Decision

**A governed vocabulary term DENOTES A REQUIREMENTS FLOOR. A consumer may select by name; explicit requirements, where given, are authoritative; and the two resolve to the same thing.**

Three parts, and each closes one of the failures above.

### 1. A term denotes a floor, not a label

Each canonical term in a governed vocabulary carries, on its own reference-data record, the minima it means — `performance` means at least 20 000 IOPS and 500 MB/s.

**This is what makes the name portable.** One provider's `SSD` and another's `performance` both qualify **iff both clear the floor**. The match is against the floor, never the string, so two providers who never agreed on vocabulary are still comparable. A term with no floor is a label, and two estates' labels are incomparable by construction.

### 2. Name-selectable, requirements-authoritative

A consumer may write the term alone and mean the floor behind it. A consumer may instead write explicit requirements. Where **both** are given, the explicit requirements drive the match.

Naming a term whose floor conflicts with the stated requirements is a **conflict**, not an override — the request is refused rather than silently resolved in either direction. A model that quietly picked one would make the same request mean different things depending on which field an implementation read first.

### 3. The provider's native answer is a realized output

The provider records the class it actually used — `gp3-encrypted` — as **realized state**, never as intent. That keeps the vendor name out of the portable request while preserving the audit answer to *"what did we actually get?"*

This is the T9 boundary in one field: intent stays portable, realization is specific, and the two are different states of the same record rather than a translation performed on the way in.

### 4. Rigor is profile-scaled, not fixed

A homelab MAY write a bare string. A sovereign estate MUST resolve to a canonical term by data reference (ADR-007 + the ADR-039 intake ladder).

The alternative — one strictness for everyone — either makes a homelab unusable or makes a regulated estate unverifiable. Posture is the existing dial for exactly this, and reusing it means no second mechanism.

### 5. A floor is whatever a second provider can be shown to meet

**It need not be numeric.** `storage_tier`'s floors are IOPS and throughput; `network_tier`'s are bandwidth and latency; a network's `zone` is a category and its floor is *"is this the kind of network the term names."*

Stated explicitly because the storage case reads as though floors must be measurable numbers, and inferring that would exclude every categorical vocabulary from this ADR — which is the opposite of the intent.

## Consequences

- **A vocabulary term without a floor is a defect, not a shortcut.** It is the label case this ADR exists to prevent, and it fails silently: everything validates, and nothing is comparable across providers.
- **A floor is not a default.** A default supplies a value the consumer did not give (rule 41 — UDLM ships none). A floor states what a *term already means*, and it does not appear in the request at all: the consumer wrote `performance`, not `min_iops: 20000`. The two are easy to confuse and NDF-001 does not apply here.
- **Curating a floor is a governance act with real weight.** Changing what `performance` means changes what every request citing it asked for, retroactively. That is why the terms are versioned reference-data records under the ADR-039 ladder rather than an enum in a schema.
- **The requirement side must be expressible, or the ADR only half-applies.** Where a class offers the name and no way to state explicit requirements, "requirements-authoritative" is unreachable. This was the state of `Compute.VM.networks` until 2026-08-10: `network_ref` was *required*, so a consumer had to name a specific network and could state no requirement at all. The fix was to make the reference optional and put requirements beside it (#497).
- **Two providers can be compared without either adopting the other's vocabulary**, which is the property the whole model is built to have. It also means a provider joining an estate does not have to rename anything — it maps its classes to floors and its existing names survive.

## Alternatives considered

- **A UDLM-wide enum of quality terms** — rejected: it picks what `fast` means for every estate (rule 41), and the terms still denote nothing, so the comparability problem is untouched.
- **Consumer names the provider's native class** — rejected: the request stops being portable the moment it is written, which is T9 with the translation moved onto the consumer.
- **Requirements only, no names** — rejected as the *default* authoring mode, though it remains fully valid. Making it mandatory means every consumer restates a floor somebody already curated, and the restatements drift from the canonical one with nothing to catch it.
- **Name wins over explicit requirements** — rejected: it makes the more specific statement the weaker one, which no reader expects.
- **Silently resolving a name/requirement conflict** — rejected: the same request would mean different things depending on which field an implementation consulted first, and the disagreement is exactly the signal worth surfacing.

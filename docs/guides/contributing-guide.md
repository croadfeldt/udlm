# Contributing to UDLM — the newcomer's on-ramp

**What this settles:** how contributing to UDLM works *socially and procedurally* — what to expect, the
shape of a pull request from fresh `main` to merge, the guidelines that keep the model coherent, and where
to go for the technical *how*. Read it once before your first contribution and you can make that first
contribution correctly. The one promise: **the gates handle the bookkeeping, so review — and your
attention — is spent on judgment.**

> Part of **[Working with UDLM](working-with-udlm.md)** — the contributor track. This is the friendly
> on-ramp; the canonical rules it routes to are in [`CONTRIBUTING.md`](../../CONTRIBUTING.md). The *technical*
> how-to — how to author a specific artifact so CI accepts it — lives in [`docs/authoring/`](../authoring).

## What to expect

Four things are true of every contribution, and knowing them up front saves a surprise later.

- **Nothing merges without the maintainer.** CI can prove a change is valid and complete; it cannot decide
  whether the change *should exist*. That call is a person's, always. The governance model — who decides
  what, and how a federated contribution is accepted — is in
  [`docs/spec/governance/federated-contribution-model.md`](../spec/governance/federated-contribution-model.md).
- **PRs are subject-scoped and small.** The unit of contribution is **one subject** — a single complete
  logical change, titled by its subject — kept to roughly **≤2–3k lines**. A larger subject is *split*
  along logical boundaries into a sequence of independently reviewable PRs, never forced into one oversized
  change. (Full rule: [`CONTRIBUTING.md`](../../CONTRIBUTING.md) §"Subject-scoped pull requests".)
- **Every human-read artifact is written for a reader who wasn't there** — the DOC-001 standard. A spec, a
  use case, a flow, an ADR, a PR description, a review comment: each is read by someone without your
  context, so it names the problem in ordinary words, carries every reference's gist in one line, and passes
  the cold-reader test. (Full rule: [`CONTRIBUTING.md`](../../CONTRIBUTING.md) §"Write for a reader who wasn't
  there".)
- **The gates do the bookkeeping.** Validity, identity, coverage, vocabulary, single-source — the automated
  checks in [`.github/workflows/validate.yml`](../../.github/workflows/validate.yml) settle all of it before a
  human looks. So review is about judgment the gates can't make, not about catching typos they already did.

## The PR lifecycle

1. **Start from a fresh `main` on a subject branch.** `git fetch origin main`, branch from it, and name the
   branch for its subject. Rebase on freshly-fetched `origin/main` before you post — never a stale base.
2. **Build the artifact.** Follow the HOWTO for your kind in [`docs/authoring/`](../authoring) — start with
   [`authoring-flow.md`](../authoring/authoring-flow.md), the map every per-kind HOWTO sits inside. Its first
   step is *reduce-to-existing*: check whether the model already composes to cover your need before you coin
   anything new.
3. **Run the gates until green.** `./scripts/signoff.sh` runs every automated gate CI runs, then prints the
   judgment checklist for you to self-answer; the full CI set is
   [`validate.yml`](../../.github/workflows/validate.yml). Fix exactly what a gate names and re-run. The
   procedure is [`docs/guides/signoff.md`](signoff.md). Signoff exits 0 only when every hard gate passes.
4. **Open a subject-scoped PR with a *Why*.** Lead the description with a short **Why** — the rationale, not
   the diff — and use it to *self-check the judgment tenets* (peer test, reduce-to-existing, adopt-by-
   reference, written-for-a-stranger). A reviewer should be able to reconstruct *why* from the repo, not
   just *what*.
5. **A reviewer raises findings.** Their job is the judgment CI can't make — is it UDLM or DCM, did it
   reduce to existing, should it exist, is it legible. See [`docs/guides/reviewing.md`](reviewing.md) for what
   they're checking and how they'll say it.
6. **The maintainer merges.** Once the findings are resolved and the sweep is clean.

**Watch the stacked-PR pitfall.** When you split a subject into a sequence and merge as you go, keep each
PR's base = `main`. Chaining a PR's base through an earlier feature branch stacks the diffs — the second PR
shows the first's changes too, and a rebase or squash-merge of the base scrambles the child. Prefer
independent PRs off `main`; only stack deliberately, and re-target to `main` the moment the parent merges.

## Guidelines — the discipline that keeps the model coherent

These are the recurring findings distilled so they're caught once, not re-litigated per PR. A good PR
self-checks them in its *Why*; the reviewer confirms. The tenets live in
[`docs/spec/principles/core-tenets.md`](../spec/principles/core-tenets.md); the full sweep is
[`CONTRIBUTING.md`](../../CONTRIBUTING.md) §"The review sweep".

- **Reduce to existing before coining (T7).** Before adding a new mechanism, show that no existing one —
  classification, profiles, references, edges, a Class, a conformance tier — composes to cover it. Reusing
  what exists is the win, not the fallback.
- **Adopt credible standards by reference (T5).** If a mature external standard already solves the concept
  (API versioning, identity, RTO/RPO, health probes), adopt it by reference rather than re-expressing it —
  or justify in the *Why* why it doesn't fit.
- **One definition, one rule, one home (single-source).** A term or normative rule is defined in exactly one
  place and referenced everywhere else; a duplicate definition is a build failure, not a style note. Every
  normative rule carries a registered `PREFIX-NNN` ID.
- **References carry their gist.** Never a bare "see ADR-NNN" — one line on what it *decided*
  ("ADR-008 — the UDLM/DCM peer test: could a conformant peer decide it differently?").
- **No estate-specific tokens in examples.** Examples use documentation placeholders — RFC 5737 IP ranges
  (`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`) and `example.com`/`example.org` names — never real
  host, site, or network identifiers. A gate scans for this.
- **Settled vocabulary only.** Use the agreed, canonical terms; a term a ruling has retired must not
  reappear in living text. (Naming authority: [`docs/spec/principles/naming-charter.md`](../spec/principles/naming-charter.md).)

## Getting started

**The repo in one paragraph.** `registry/` is the model — resource types, Classes, instances, policies,
providers, and the `*.schema.json` meta-schemas they validate against. `use-cases/` is the corpus — the
scenarios that exercise the model. `docs/` holds the guides you're reading, the decision records
([`docs/adr/`](../adr), each row of [`adr/README.md`](../adr/README.md) carrying its gist), and the lifecycle
flows ([`docs/flows/`](../flows)). `tests/` plus [`.github/workflows/validate.yml`](../../.github/workflows/validate.yml)
are the gates.

**Run the gates locally.** From the repo root, `./scripts/signoff.sh` — it runs the automated gates and
prints the judgment checklist. Do this before you open any PR; green locally means green in CI.

**Where to ask.** Open an issue or a draft PR for a question about scope or direction; the maintainer and
the governance model ([`docs/spec/governance/`](../spec/governance/)) are the deciding authority for what lands and how.

## The four roles — a short map

You've arrived at UDLM to do one of four things. This guide is the fourth; here's where the others live.

| You're here to… | You're a… | Start at |
|---|---|---|
| Build something *in* the model — a type, Class, policy, provider, reference data, or corpus artifact | **author** | [`docs/authoring/`](../authoring) |
| Judge someone else's contribution | **reviewer** | [`docs/guides/reviewing.md`](reviewing.md) |
| Build a system that *uses* the model — a control plane, provider backend, or dashboard | **consumer / builder** | [`docs/guides/consuming.md`](consuming.md) |
| Contribute to the project — process, expectations, guidelines | **contributor** | this guide → [`CONTRIBUTING.md`](../../CONTRIBUTING.md) |

By contributing you agree your work is licensed under Apache License 2.0, matching the project.

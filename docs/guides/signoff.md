# Pre-post signoff procedure

**Run this before opening any PR or publishing any content.** It has two tiers: **automated gates** (a script
that must pass) and a **judgment checklist** (self-checks a script can't make). It is the operational form of
the [review sweep](../../CONTRIBUTING.md#the-review-sweep--what-every-pr-is-checked-against) — the sweep says
*what* is checked; this says *how to run it before you post*.

## 1 · Automated gates — `scripts/signoff.sh`

```bash
./scripts/signoff.sh              # checks against origin/main
./scripts/signoff.sh <base-ref>   # e.g. a release branch
```

It runs every gate CI runs, reports pass/fail per gate, and **exits non-zero if any hard gate fails** —
so it doubles as a local pre-flight for the CI in `.github/workflows/validate.yml`. The gate list is not
restated in the script: `scripts/ci-steps.py` derives it from `validate.yml`, so a step added to CI is a
step signoff runs. A step is hard unless the workflow marks it report-only (a trailing
`|| echo "::warning::…"`), in which case signoff reports it and does not block. Among the steps: registry
valid-by-construction and meta-schema validation, the estate-token scrub, single-source (rule IDs and
vocabularies; `SPEC-DESIGN-REQUIREMENTS.md` rule 33, ADR-028), model vocabulary, the version/compat gate,
readability, and the report-only standards-registered check.

A green run is necessary, **not sufficient** — CI is the backstop, not the sign-off; the judgment items below
are where most review findings actually come from.

## 2 · Judgment checklist — self-check (the script prints this too)

The recurring review findings, distilled. A good PR self-checks these in its *Why*.

- **Scope — the peer test (ADR-008).** Could an independent conformant peer decide this differently and still
  be valid? *Yes → DCM* (Policy/implementation); *No → UDLM* (portable substrate). Implementation mechanism in the
  portable model is a finding.
- **Reduce to existing (T7).** No net-new mechanism unless the *Why* shows nothing existing composes to cover it.
- **Adopt by reference (T5).** Don't re-express a concept a credible external standard already solves.
- **Adopt tools by reference (T8).** Where a mature tool owns the mechanism, wrap it as a Provider — don't reimplement.
- **Data point earns its keep.** Every stored field has a real consumer *or* is a derived predicate — no
  duplicated functionality (the data twin of T7).
- **Written for engineers** (DOC-001, `CONTRIBUTING.md`). Audience is engineering teams. **Strip internal
  working-context — session/working-set labels, private ticket numbers, colleague names, internal tool
  artifacts.** Every reference carries its gist in one line. Concise; no duplication.
- **Naming.** Canonical terms only (`docs/spec/principles/naming-charter.md`); no unratified renames.
- **Sizing.** ≤ 2–3k lines, one complete subject; split larger changes along logical boundaries.
- **Document the why.** Rationale lives in the repo (design note / tenet / ADR), not just the diff.
- **Git hygiene.** Rebased on a **freshly-fetched** `origin/main` (fetch before any `reset --hard`).

## 3 · The scrub is a hard line for shared content

The estate-token gate is automated; **colleague names, customer names, private tickets, and internal
session/working-context are a *manual* scrub** under "written for engineers" — and they are non-negotiable for
any public or partner-shared artifact. When in doubt, keep the working analysis in a private file and publish
only the clean result.

## Sign-off

Post only when: `scripts/signoff.sh` exits 0 **and** every judgment item is satisfied (or explicitly N/A with a
one-line reason in the PR *Why*).

---

*Adopting this in another repo* (e.g. DCM): copy `scripts/signoff.sh`, point it at that repo's check set, and
reference this procedure — the judgment checklist is repo-agnostic.

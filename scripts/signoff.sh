#!/usr/bin/env bash
# Pre-post signoff — run before opening any PR or publishing content.
# Runs every automated gate, then prints the human judgment checklist.
# Exit 0 only if all HARD gates pass. Procedure: docs/guides/signoff.md.
set -uo pipefail
cd "$(git rev-parse --show-toplevel)" || exit 2
base="${1:-origin/main}"
fail=0; warn=0
run() { # run "name" hard|soft cmd...
  local name="$1" kind="$2"; shift 2
  if out=$("$@" 2>&1); then printf '  \033[32m✓\033[0m %s\n' "$name"
  elif [ "$kind" = soft ]; then printf '  \033[33m!\033[0m %s (report-only)\n' "$name"; warn=$((warn+1))
  else printf '  \033[31m✗ %s\033[0m\n' "$name"; echo "$out" | tail -6 | sed 's/^/      /'; fail=$((fail+1)); fi
}
echo "== Automated gates =="
# The gate list is DERIVED from .github/workflows/validate.yml, never restated here. A restated
# list drifts: 20 of CI's steps were missing from this script, and twice in one week a PR passed
# signoff and failed CI. Adding a step to CI is now the only edit needed — see scripts/ci-steps.py.
steps=$(python3 scripts/ci-steps.py) || { echo "  could not read the CI step list"; exit 2; }
# Fail closed on a short list. An empty or truncated read would run nothing and report PASS, which
# is the failure this script exists to prevent — a green signoff that checked nothing.
n_steps=$(printf '%s\n' "$steps" | grep -c .)
if [ "$n_steps" -lt 20 ]; then
  printf '\033[31m  refusing to run: derived only %s step(s) from validate.yml.\033[0m\n' "$n_steps"
  echo "  A short list means the workflow moved or the parser broke. Passing here would be vacuous."
  exit 2
fi
while IFS=$'\t' read -r name kind cmd; do
  [ -z "$cmd" ] && continue
  cmd=${cmd//origin\/main/$base}          # honour a non-default base ref
  run "$name" "$kind" bash -c "$cmd"
done <<< "$steps"

echo ""
echo "== Judgment checklist (self-check — not automatable) =="
cat <<'EOF'
  [ ] Scope — peer test (ADR-008): computed/negotiated/executed -> DCM; portable data -> UDLM
  [ ] Reduce to existing (T7): no net-new mechanism unless nothing composes to cover it
  [ ] Adopt by reference (T5): don't re-express a credible external standard
  [ ] Adopt tools by reference (T8): wrap a mature tool as a Provider, don't reimplement
  [ ] Data point earns its keep: has a real consumer OR is a derived predicate (no duplicate data)
  [ ] Written for engineers: no internal/session refs, no PII/colleague names, references carry their gist
  [ ] Naming: canonical terms only (docs/spec/principles/naming-charter.md); no unratified renames
  [ ] Sizing: <=2-3k lines, one subject; split if larger
  [ ] Document the why: rationale in the repo (design note / tenet / ADR), not just the diff
  [ ] Git hygiene: rebased on freshly-fetched origin/main
  [ ] Cleanliness Q1-Q7 semantic residues (single-source prose, vocab drift in prose,
      boundary/ADR-008, provider-neutrality, doc scoping) — the nine-question brief:
      croadfeldt/dav docs/repo-cleanliness-review.md
EOF
echo ""
if [ "$fail" -gt 0 ]; then printf '\033[31mSIGNOFF FAILED — %d hard gate(s) failed.\033[0m\n' "$fail"; exit 1; fi
printf '\033[32mAutomated gates PASS'; [ "$warn" -gt 0 ] && printf ' (%d report-only)' "$warn"; printf '.\033[0m Complete the judgment checklist, then post.\n'

#!/usr/bin/env bash
# Pre-post signoff — run before opening any PR or publishing content.
# Runs every automated gate, then prints the human judgment checklist.
# Exit 0 only if all HARD gates pass. Procedure: docs/signoff.md.
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
run "registry valid-by-construction"    hard python3 registry/tools/validate.py
run "registry meta-schema"              hard python3 tests/validate_registry.py
run "estate-token scrub"                hard python3 tests/check_estate_tokens.py
run "single-source (rule IDs)"          hard python3 tests/check_single_source.py
run "single-source (definitions)"       hard python3 tests/check_definition_single_source.py
run "model vocabulary"                  hard python3 tests/check_model_vocabulary.py
run "session narration"                 hard python3 tests/check_session_narration.py
run "profile tables"                    hard python3 tests/check_profile_tables.py
run "compat-check compiles"             hard python3 -c "compile(open('registry/tools/compat-check.py').read(),'x','exec')"
run "version / compat gate vs $base"    hard python3 tests/ci_compat_gate.py "$base"
run "standards registered"              soft python3 tests/check_standards_registered.py
echo ""
echo "== Judgment checklist (self-check — not automatable) =="
cat <<'EOF'
  [ ] Scope — peer test (ADR-008): computed/negotiated/executed -> DCM; portable data -> UDLM
  [ ] Reduce to existing (T7): no net-new mechanism unless nothing composes to cover it
  [ ] Adopt by reference (T5): don't re-express a credible external standard
  [ ] Adopt tools by reference (T8): wrap a mature tool as a Provider, don't reimplement
  [ ] Data point earns its keep: has a real consumer OR is a derived predicate (no duplicate data)
  [ ] Written for engineers: no internal/session refs, no PII/colleague names, references carry their gist
  [ ] Naming: canonical terms only (design-principles/naming-charter.md); no unratified renames
  [ ] Sizing: <=2-3k lines, one subject; split if larger
  [ ] Document the why: rationale in the repo (design note / tenet / ADR), not just the diff
  [ ] Git hygiene: rebased on freshly-fetched origin/main
EOF
echo ""
if [ "$fail" -gt 0 ]; then printf '\033[31mSIGNOFF FAILED — %d hard gate(s) failed.\033[0m\n' "$fail"; exit 1; fi
printf '\033[32mAutomated gates PASS'; [ "$warn" -gt 0 ] && printf ' (%d report-only)' "$warn"; printf '.\033[0m Complete the judgment checklist, then post.\n'

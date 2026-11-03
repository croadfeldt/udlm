#!/usr/bin/env bash
# Regenerate every derived file after a class change, in the order CI checks them.
# Usage: scripts/regen.sh [base-ref]   (base-ref defaults to origin/main)
#
# Five files are derived from the classes and must be committed with the change that moved them:
# the served specs under registry/generated/, registry/TYPE-CATALOG.md, registry/pin-manifest.json,
# the coverage backlog, and the model-health report. Each has a `--check` step in CI that fails when
# it is stale. Run this once after editing a class, then commit what it changed.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
base="${1:-origin/main}"
# The pin manifest is append-only against the base branch (registry/VERSIONING.md, publish law).
# Start from the base copy so a regenerate adds rows and never rewrites earlier ones.
if git rev-parse --verify -q "$base" >/dev/null; then
  git checkout "$base" -- registry/pin-manifest.json
fi
python3 registry/tools/generate_class_specs.py
python3 registry/tools/generate_type_catalog.py
python3 registry/tools/generate_pin_manifest.py
python3 registry/tools/spec_coverage.py
python3 registry/tools/model_health.py
echo
echo "regenerated. Commit what changed:"
git status --short -- registry/generated registry/TYPE-CATALOG.md registry/pin-manifest.json registry/spec-coverage-backlog.yaml registry/MODEL-HEALTH.md registry/model-health.json | sed 's/^/  /'

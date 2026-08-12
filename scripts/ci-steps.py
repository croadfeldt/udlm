#!/usr/bin/env python3
"""Emit the CI step list, so signoff runs what CI runs.

`scripts/signoff.sh` used to restate the gate list by hand. It drifted: 20 of validate.yml's steps
were missing from it, and twice in one week a PR passed signoff and failed CI — once on a stale
generated artifact, once on a gate the author had added to CI and not to signoff.

A restated list is the bug. This derives it, so a step added to CI is a step signoff runs, with no
second edit and nothing to forget.

Output is one `name<TAB>kind<TAB>command` per line. `kind` is `hard` unless the workflow marks the
step soft (a trailing `|| echo "::warning::…"`, which is how the workflow says "report, do not
block"). `name` comes from NAMES below when the command is known, else from the script's own
filename — a derived name is worse prose than a curated one and infinitely better than a step that
does not run.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW = os.path.join(ROOT, ".github", "workflows", "validate.yml")

# Curated display names. A command absent here still runs — it is named from its filename.
NAMES = {
    "python3 registry/tools/validate.py": "registry valid-by-construction",
    "python3 tests/validate_registry.py": "registry meta-schema",
    "python3 tests/check_estate_tokens.py": "estate-token scrub",
    "python3 tests/check_single_source.py": "single-source (rule IDs + vocabularies)",
    "python3 tests/check_conformance_constants.py": "no coined constant in a certification rule (CNF-001)",
    "python3 tests/check_adr_retirement_claims.py": "no ADR claims a retirement the schemas contradict (RET-001)",
    "python3 tests/check_layer_limits.py": "layer lineage + envelope containment (LAY-009/010)",
    "python3 tests/check_tier_state_conflation.py": "no definition tier described as a state (TIER-001)",
    "python3 tests/check_duplicate_yaml_keys.py": "no duplicate YAML mapping keys (DUP-001)",
    "python3 tests/check_definition_single_source.py": "single-source (definitions)",
    "python3 tests/check_implementation_neutrality.py": "implementation-neutral normative tier (IMP-001)",
    "python3 tests/check_adr_citations.py": "cited ADRs resolve (ADR-CITE-001)",
    "python3 tests/check_model_vocabulary.py": "model vocabulary",
    "python3 tests/check_session_narration.py": "session narration",
    "python3 tests/check_profile_tables.py": "profile tables",
    "python3 tests/check_offer_collapse.py": "Offer collapse (selection inside the offer)",
    "python3 tests/check_no_shipped_defaults.py": "No UDLM-shipped defaults (NDF-001)",
    "python3 tests/check_cited_schema_files.py": "Cited schema files exist (CSF-001)",
    "python3 tests/check_grant_derivation.py": "Required-grant set derives (GRD-001)",
    "python3 tests/check_group_invariants.py": "Structural invariants (GRP-INV-001/002/005/006)",
    "python3 tests/check_composition_promotion.py": "Promotion is a round trip (ING-017/018/019)",
    "python3 tests/check_fulfillment_conditions.py": "Blocked members are actionable (FUL-001/002/003)",
    "python3 tests/check_must_reject.py": "Negative corpus is refused (MRJ-001)",
    "python3 tests/check_example_coverage.py": "Examples say what they prove (ECV-001)",
    "python3 tests/check_schema_dialect.py": "Schemas declare Draft 2020-12 (SCD-001)",
    "python3 tests/check_conformance_consolidation.py": "§6 consolidates its sources (CNS-001)",
    "python3 tests/check_uc_traceability.py": "UC traceability (flow -> corpus)",
    "python3 tests/check_policy_facts.py": "Policy-fact vocabulary (policy-contract 2.1)",
    "python3 tests/check_action_vocabulary.py": "One action vocabulary (ACT-001/002/003)",
    "python3 tests/check_triad_coherence.py": "Capability/action/thing triad closes (TRI-001/002/003)",
    "python3 tests/check_policy_boundary.py": "Policy-engine boundary (ADR-065)",
    "python3 tests/check_urf.py": "URF grammar (identifier-scheme 9)",
    "python3 tests/check_urf_conformance.py": "URF conformance (dereference + portability)",
    "python3 registry/tools/fuzz_urf.py": "URF grammar fuzz (combinatorial)",
    "python3 tests/check_type_standard.py": "type base standard (rule 36)",
    "python3 tests/check_identity_integrity.py": "identity integrity (ADR-051)",
    "python3 tests/check_class_liskov.py": "class Liskov (refine, never contradict)",
    "python3 tests/check_class_paths.py": "class path <-> record (CLS-PATH-001)",
    "python3 registry/tools/generate_class_specs.py --check": "generated specs are fresh (GEN-001)",
    "python3 registry/tools/generate_type_catalog.py --check": "TYPE-CATALOG is fresh",
    "python3 registry/tools/generate_pin_manifest.py --check": "pin manifest (current+append-only)",
    "python3 registry/tools/model_health.py --check": "model health is fresh",
    "python3 registry/tools/spec_coverage.py --check": "spec coverage (COV-001)",
    "python3 tests/ci_compat_gate.py origin/main": "version / compat gate vs origin/main",
}


def steps():
    out, seen = [], set()
    text = open(WORKFLOW, encoding="utf-8").read()
    for raw in re.findall(r"run:\s*\|?\s*\n?\s*(python3 [^\n]+|bash [^\n]+|\./[^\n]+)", text):
        cmd = raw.strip()
        # the workflow's own way of saying "report, do not block"
        kind = "soft" if re.search(r'\|\|\s*echo\s+"?::warning', cmd) else "hard"
        cmd = re.sub(r'\s*\|\|\s*echo\s+"?::warning.*$', "", cmd).strip()
        if cmd in seen:
            continue
        seen.add(cmd)
        name = NAMES.get(cmd)
        if not name:
            m = re.search(r"([\w-]+)\.py", cmd)
            name = (m.group(1).replace("check_", "").replace("_", " ") if m else cmd[:40])
            if "--check" in cmd:
                name += " (--check)"
        out.append((name, kind, cmd))
    return out


if __name__ == "__main__":
    for name, kind, cmd in steps():
        print(f"{name}\t{kind}\t{cmd}")
    if "--count" in sys.argv:
        print(f"{len(steps())} step(s)", file=sys.stderr)

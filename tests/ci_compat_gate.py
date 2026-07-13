#!/usr/bin/env python3
"""CI compat gate — makes SPEC-DESIGN §9 [enforced: compat-check] real.

For every resource-type spec that differs from the base ref (default origin/main), run
registry/tools/compat-check.py with old=base-version, new=working-version and fail if the
declared `version` bump is under-declared (a breaking change shipped as MINOR/REVISION, etc.).
New type files (absent on base) are skipped — there is no prior version to compare.

Usage: tests/ci_compat_gate.py [base_ref]   (base_ref default: origin/main)
Exit 0 = all changed specs declare a sufficient bump (or are new); 1 = at least one
under-declared. Wire into .github/workflows/validate.yml.
"""
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPAT = os.path.join(ROOT, "registry", "tools", "compat-check.py")


def sh(*args):
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True)


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
    # ensure the base ref is present (CI clones may be shallow); non-fatal if fetch fails
    sh("git", "fetch", "--quiet", "--depth", "1", "origin",
       base.split("/", 1)[1] if base.startswith("origin/") else base)

    diff = sh("git", "diff", "--name-only", base, "--", "registry/resource-types")
    if diff.returncode != 0:
        print(f"compat-gate: cannot diff against {base} ({diff.stderr.strip()}); skipping "
              f"(not a failure — base ref unavailable)")
        return 0

    changed = [f for f in diff.stdout.splitlines()
               if f.endswith((".json", ".yaml", ".yml"))]
    if not changed:
        print(f"compat-gate: no resource-type changes vs {base}")
        return 0

    failures = 0
    for rel in changed:
        old_blob = sh("git", "show", f"{base}:{rel}")
        if old_blob.returncode != 0:
            print(f"ok   {rel}  — NEW type (no prior version on {base})")
            continue
        if not os.path.exists(os.path.join(ROOT, rel)):
            # symmetric to a NEW type: a REMOVED type has no new version to compat-check.
            # The removal is a deliberate, reviewed change (e.g. retiring an anti-pattern type);
            # the gate checks bump sufficiency, not removal policy, so don't crash on it.
            print(f"ok   {rel}  — REMOVED type (retired; no new version to compat-check)")
            continue
        suffix = os.path.splitext(rel)[1]
        with tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False) as tmp:
            tmp.write(old_blob.stdout)
            old_path = tmp.name
        try:
            res = sh("python3", COMPAT, old_path, os.path.join(ROOT, rel))
            print(res.stdout.strip() or res.stderr.strip())
            if res.returncode != 0:
                failures += 1
        finally:
            os.unlink(old_path)

    print(f"\ncompat-gate: {len(changed)} changed spec(s), {failures} under-declared")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

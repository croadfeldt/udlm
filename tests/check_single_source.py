#!/usr/bin/env python3
"""Single-source guard for UDLM rule IDs — registry-backed.

Every normative rule carries a stable ID (ENT-006, PRV-009, DPO-003, ...). The convention
(registry/rule-id-naming.md, ADR-028) is: **one prefix = one rule family = one home file.**
A rule is *defined* by an ID-first Markdown table row (`| `PFX-NNN` | ... |`); every other
mention is a citation. The single source of truth for which prefix lives where is
`registry/rule-id-registry.yaml` (validated against rule-id-registry.schema.json).

This check reads that registry and, across the normative spec surface (tests/, .github/,
docs/internal/ excluded), FAILS on:
  - UNREGISTERED  — a prefix is defined in the docs but absent from the registry.
  - OUT-OF-HOME   — a prefix is defined in a file other than its registered `home`
                    (unless that file is grandfathered in the prefix's `baseline_spread`).
  - ID-COLLISION  — the same full ID is defined in >1 file (the sharpest out-of-home case).
  - ID-REPEATED   — the same full ID is defined twice in ONE file. Found 2026-08-09 by making the
                    mistake: a duplicated row passed cleanly, because the collision map keys on the
                    set of files and a set collapses two rows in one file to a single entry.
  - REGISTRY      — the registry itself is malformed (schema-invalid, duplicate prefix,
                    or a `home` path that does not exist).

**The vocabulary arm (VOC-*).** SPEC-DESIGN §33 reads "every normative rule, VOCABULARY, or
wire-shape is defined in exactly one file" — and until 2026-08-11 this check read only the rule half,
because a rule is a Markdown table row and a vocabulary is a JSON enum. Nothing looked at the enums.
The cost was measured rather than assumed: the action vocabulary had forked into FIVE literal copies
(audit-record, audit-leaf, commit-log-entry, the governance matrix, universal-audit's table) and six
other closed lists were declared literally in two or three files each. Every one passed CI, because
a list checked against nothing always looks complete.

A closed vocabulary may be DECLARED once. Every other site is one of:
  - a `$ref` to that declaration — the JSON Schema mechanism, resolved through validate.py's ref
    store, so it is one definition rather than an agreeing copy;
  - a PROJECTION carrying `x-generated-from: <path>` — for a vocabulary whose home is a YAML
    taxonomy, which a JSON enum cannot `$ref`. The gate proves the projection equals its source, so
    the claim is checkable rather than a comment.

  - VOC-001  the same closed list (>= MIN_MEMBERS) is literal in >1 authored file, and is neither
             baselined nor a proven projection. This is the arm that would have caught the action
             fork on the day it was authored.
  - VOC-002  an `x-generated-from` claim that does not hold — the projection has drifted from its
             source. Worse than an undeclared copy: it asserts a guarantee it is not keeping.
  - VOC-003  `x-generated-from` names a file that does not exist or carries no terms.
  - VOC-004  a VOCAB_BASELINE entry that no longer duplicates — stale, so it gets removed. Without
             this the baseline silently becomes a permanent exemption list, which is how the debt
             stopped being visible the last time.

registry/generated/** is excluded: it is a projection of the authored classes and is already proven
by `registry/tools/generate_class_specs.py --check`. Checking it here would report one fork three
times and hide the authored source.

A `baseline_spread` entry that no longer contains a definition is reported STALE (non-failing)
so it gets removed — the check ratchets toward zero debt. Exit 0 clean, 1 on any failure.
"""
import glob
import json
import os
import re
import sys

import yaml

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY = os.path.join(REPO, "registry", "rule-id-registry.yaml")
SCHEMA = os.path.join(REPO, "registry", "rule-id-registry.schema.json")

# --- the vocabulary arm ------------------------------------------------------------------------
# Below this size a repeated list is more likely a coincidence than a fork (two schemas both
# allowing ["low","medium","high"] are not necessarily one vocabulary). Four is where the shared
# lists in this repo actually start, measured rather than picked.
MIN_MEMBERS = 4

# KNOWN DEBT, each with the RULING it is waiting on rather than a bare exemption. An entry here
# WARNS; anything else FAILS. VOC-004 reports an entry that no longer duplicates, so this list can
# only shrink.
VOCAB_BASELINE = {
    frozenset(("physical", "virtual", "passthrough", "partition")):
        "`device_class` is declared literally by seven classes and narrowed differently by each "
        "(common-elements.md §7 carries six values; Hardware.Processor offers four). The fix is a "
        "SharedDataElement at the Hardware scope that children narrow under ADR-038, NOT a $ref — "
        "narrowing is the point, and a $ref cannot narrow. Needs the element authored first (#520).",
    frozenset(("proposed", "under-review", "canonical", "deprecated")):
        "The curation ladder, declared literally by Knowledge.TaxonomyTerm and Knowledge.Capability. "
        "Same shape as device_class and the same fix — one SharedDataElement at the Knowledge scope "
        "(#520). Baselined together because splitting them would mean authoring the mechanism twice.",
}

# Directories that are not the normative spec surface.
SKIP_DIRS = {".git", "node_modules", "docs/internal", "tests", ".github"}

# Definition = first non-empty cell of a table row is a rule ID (optionally hyphen-segmented,
# optionally sub-numbered). A sub-number (WIR-012.1) is a requirement that ELABORATES its parent
# rather than standing alone — the maintainer's preference for fewer top-level ids with detail
# grouped under them. It is a distinct definition for single-source purposes: WIR-012.1 may be
# defined once, exactly like WIR-012, and the two do not collide with each other.
ROW_RE = re.compile(r"^\|\s*`?([A-Z][A-Z0-9]{1,7}(?:-[A-Z]{1,5})*-\d{2,3}(?:\.\d{1,2})?)`?\s*\|")
# The leading prefix of a full ID (REG-DP-002 -> REG; ENT-006 -> ENT).
LEAD_RE = re.compile(r"^[A-Z][A-Z0-9]{1,5}")


def _closed_lists(node, path, out, src):
    """Every closed list in a document, with where it sits. Recurses into $defs and allOf branches —
    a copy nested inside a branch is still a copy, which is how the fourth action copy hid."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "enum" and isinstance(v, list) and all(isinstance(x, str) for x in v) \
                    and (len(v) >= MIN_MEMBERS or node.get("x-generated-from")):
                # MIN_MEMBERS gates the DUPLICATE hunt, never a declared projection. Found by
                # probing: deleting a member from a shared vocabulary dropped it to three and the
                # projection check went silent — so the one edit most likely to break a projection
                # was also the one that stopped it being checked.
                out.setdefault(frozenset(x.lower() for x in v), []).append(
                    (src, path + "/enum", node.get("x-generated-from")))
            else:
                _closed_lists(v, f"{path}/{k}", out, src)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            _closed_lists(v, f"{path}[{i}]", out, src)


def _source_terms(rel):
    """The term set a projection claims to be generated from.

    A YAML source, because a JSON one would be `$ref`-able and so would need no projection at all.
    The claim may name where the terms live: `registry/edge-types.yaml#/edge_types/*/edge_type`.
    A bare path defaults to `#/terms/*/term`, the governed-taxonomy shape, so the common case stays
    short. Explicit rather than guessed — a gate that infers where the terms are will one day infer
    wrong and report a clean pass over the wrong list."""
    rel, _, pointer = rel.partition("#")
    path = os.path.join(REPO, rel)
    if not os.path.exists(path):
        return None
    doc = yaml.safe_load(open(path, encoding="utf-8")) or {}
    listkey, termkey = "terms", "term"
    if pointer:
        parts = [p for p in pointer.split("/") if p and p != "*"]
        if len(parts) != 2:
            return None
        listkey, termkey = parts
    terms = {t[termkey].lower() for t in doc.get(listkey, [])
             if isinstance(t, dict) and isinstance(t.get(termkey), str)}
    return {t for t in terms if t != doc.get("root")} or None


def check_vocabularies():
    """VOC-001..004. Returns (failure lines, note lines, counts)."""
    found = {}
    files = [f for f in glob.glob(os.path.join(REPO, "registry", "**", "*.json"), recursive=True)
             if os.sep + "generated" + os.sep not in f]
    files += glob.glob(os.path.join(REPO, "registry", "classes", "**", "*.yaml"), recursive=True)
    for f in sorted(files):
        rel = os.path.relpath(f, REPO)
        try:
            doc = (json.load(open(f, encoding="utf-8")) if f.endswith(".json")
                   else yaml.safe_load(open(f, encoding="utf-8")))
        except Exception:
            continue
        _closed_lists(doc, "", found, rel)

    fails, notes = [], []
    used_baseline = set()
    n_dupe = 0

    for members, sites in sorted(found.items(), key=lambda kv: sorted(kv[0])):
        if len({s for s, _, _ in sites}) < 2:
            # Single-file, but a projection claim still has to hold — an unchecked claim is the
            # only thing worse than no claim.
            for src, where, gen in sites:
                if gen:
                    fails.extend(_check_projection(members, src, where, gen))
            continue
        n_dupe += 1
        gens = {g for _, _, g in sites}
        if None not in gens:                       # every copy is a declared projection
            for src, where, gen in sites:
                fails.extend(_check_projection(members, src, where, gen))
            continue
        if members in VOCAB_BASELINE:
            used_baseline.add(members)
            notes.append(f"  WARN [VOC-001] {sorted(members)[:4]}... in "
                         f"{len({s for s, _, _ in sites})} files — baselined: "
                         f"{VOCAB_BASELINE[members]}")
            continue
        fails.append(f"VOC-001 one vocabulary, {len({s for s,_,_ in sites})} literal declarations "
                     f"— {sorted(members)}")
        for src, where, _ in sites:
            fails.append(f"          {src}{where}")
        fails.append("          Fix: declare it once (common-elements.schema.json $defs) and $ref "
                     "the rest, or — if its home is a YAML taxonomy — mark each projection "
                     "`x-generated-from: <path>` so this gate can prove they agree.")

    for members in VOCAB_BASELINE:
        if members not in used_baseline:
            fails.append(f"VOC-004 stale baseline: {sorted(members)} no longer duplicates — remove "
                         f"it from VOCAB_BASELINE so the debt list keeps meaning something")

    return fails, notes, (len(found), n_dupe)


def _check_projection(members, src, where, gen):
    terms = _source_terms(gen)
    if terms is None:
        return [f"VOC-003 {src}{where} claims x-generated-from: {gen}, which does not exist or "
                f"carries no terms — a source nobody can read is not a source"]
    if members != terms:
        extra, missing = sorted(members - terms), sorted(terms - members)
        return [f"VOC-002 {src}{where} has DRIFTED from {gen} — "
                + (f"not in the source: {extra}. " if extra else "")
                + (f"missing from the projection: {missing}." if missing else "")
                + " A declared projection that does not match its source asserts a guarantee it is "
                  "not keeping."]
    return []


def load_registry():
    """Return (entries, errors). Validates against the schema when jsonschema is available."""
    errors = []
    try:
        import yaml
    except ImportError:
        return None, ["pyyaml required to load the rule-id registry"]
    try:
        reg = yaml.safe_load(open(REGISTRY, encoding="utf-8"))
    except (OSError, yaml.YAMLError) as e:
        return None, [f"cannot load {os.path.relpath(REGISTRY, REPO)}: {e}"]

    try:
        import json
        from jsonschema import Draft202012Validator
        schema = json.load(open(SCHEMA, encoding="utf-8"))
        for err in sorted(Draft202012Validator(schema).iter_errors(reg), key=lambda e: list(e.path)):
            loc = "/".join(str(p) for p in err.path) or "(root)"
            errors.append(f"registry schema: {loc}: {err.message}")
    except ImportError:
        pass  # jsonschema optional locally; CI installs it

    entries = (reg or {}).get("prefixes", [])
    seen = set()
    for e in entries:
        pfx = e.get("prefix")
        if pfx in seen:
            errors.append(f"registry: duplicate prefix '{pfx}'")
        seen.add(pfx)
        home = e.get("home")
        if home and not os.path.exists(os.path.join(REPO, home)):
            errors.append(f"registry: prefix '{pfx}' home '{home}' does not exist")
        for field in ("baseline_spread", "additional_homes"):
            for f in e.get(field, []):
                if not os.path.exists(os.path.join(REPO, f)):
                    errors.append(f"registry: prefix '{pfx}' {field} '{f}' does not exist")
    return entries, errors


def spec_md_files():
    for root, dirs, files in os.walk(REPO):
        rel = os.path.relpath(root, REPO)
        dirs[:] = [d for d in dirs if os.path.join(rel, d).lstrip("./") not in SKIP_DIRS
                   and d not in SKIP_DIRS]
        for f in files:
            if f.endswith(".md"):
                yield os.path.join(root, f)


def main():
    entries, reg_errors = load_registry()
    if entries is None:
        for e in reg_errors:
            print(f"  ✗ {e}")
        return 1

    home = {e["prefix"]: e["home"] for e in entries}
    baseline = {e["prefix"]: set(e.get("baseline_spread", [])) for e in entries}
    # additional_homes: SANCTIONED co-definition files (a family deliberately spans >1 doc
    # with a coordinated number space and no duplicate ID — see rule-id-naming.md). Unlike
    # baseline_spread (debt to burn down), these are permanent and not reported as debt. The
    # duplicate-ID-number invariant is still enforced (a full ID in >1 file always fails
    # unless grandfathered in baseline_spread), so a genuine clash is still caught.
    sanctioned = {e["prefix"]: set(e.get("additional_homes", [])) for e in entries}

    # full_id -> set(files); prefix -> file -> set(numbers)
    defined = {}
    in_file = {}   # (id, file) -> occurrences, for the same-file repeat
    prefix_files = {}
    for path in spec_md_files():
        rel = os.path.relpath(path, REPO)
        try:
            lines = open(path, encoding="utf-8").read().splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for line in lines:
            m = ROW_RE.match(line)
            if not m:
                continue
            full = m.group(1)
            pfx = LEAD_RE.match(full).group(0)
            defined.setdefault(full, set()).add(rel)
            # `defined` maps id -> set of FILES, so two rows for one id in ONE file collapse to a
            # single entry and the collision is invisible. Counted separately: a rule defined twice
            # in its own home can carry two different texts, and the later one silently wins for a
            # reader who scrolls.
            in_file[(full, rel)] = in_file.get((full, rel), 0) + 1
            prefix_files.setdefault(pfx, set()).add(rel)

    unregistered = sorted(p for p in prefix_files if p not in home)

    out_of_home = []          # (prefix, file)
    used_baseline = set()      # (prefix, file) baseline_spread that actually matched
    used_sanctioned = set()    # (prefix, file) additional_homes that actually matched
    for pfx, files in prefix_files.items():
        if pfx not in home:
            continue
        for f in sorted(files):
            if f == home[pfx]:
                continue
            if f in sanctioned.get(pfx, set()):
                used_sanctioned.add((pfx, f))
            elif f in baseline.get(pfx, set()):
                used_baseline.add((pfx, f))
            else:
                out_of_home.append((pfx, f))

    collisions = {i: sorted(fs) for i, fs in defined.items() if len(fs) > 1}
    # An id-collision is a NEW failure only if it isn't fully covered by baselines/home.
    new_collisions = {}
    for i, fs in collisions.items():
        pfx = LEAD_RE.match(i).group(0)
        allowed = {home.get(pfx)} | baseline.get(pfx, set())
        if any(f not in allowed for f in fs):
            new_collisions[i] = fs

    stale = sorted(
        [(pfx, f, "baseline_spread") for pfx, bs in baseline.items() for f in bs
         if (pfx, f) not in used_baseline]
        + [(pfx, f, "additional_homes") for pfx, ah in sanctioned.items() for f in ah
           if (pfx, f) not in used_sanctioned])

    voc_fails, voc_notes, (n_lists, n_dupe) = check_vocabularies()

    n_sanctioned = sum(len(v) for v in sanctioned.values())
    n_debt = sum(len(v) for v in baseline.values())
    print(f"rule-id single-source: {len(home)} registered prefix(es); "
          f"{len(defined)} rule IDs across the normative surface; "
          f"{len(collisions)} collide ({len(collisions) - len(new_collisions)} baselined); "
          f"{n_sanctioned} sanctioned co-home(s), {n_debt} spread-debt entr(y/ies).")
    print(f"vocabulary single-source: {n_lists} closed list(s) >= {MIN_MEMBERS} members across the "
          f"authored registry; {n_dupe} declared in more than one file "
          f"({len(VOCAB_BASELINE)} baselined).")
    for n in voc_notes:
        print(n)

    if stale:
        print("\nSTALE registry entries (no definition there anymore — remove from the registry):")
        for pfx, f, field in stale:
            print(f"  - {pfx}: {f} ({field})")

    fail = False
    if voc_fails:
        print("\nVOCABULARY single-source violations (SPEC-DESIGN §33 — one home per vocabulary):")
        for m in voc_fails:
            print(f"  {'✗ ' if m[:3] == 'VOC' else '   '}{m}")
        fail = True
    for e in reg_errors:
        print(f"  ✗ {e}"); fail = True
    if unregistered:
        print("\nUNREGISTERED prefixes (add to registry/rule-id-registry.yaml before use):")
        for p in unregistered:
            print(f"  ✗ {p}-* defined in: {', '.join(sorted(prefix_files[p]))}")
        fail = True
    if out_of_home:
        print("\nOUT-OF-HOME definitions (a prefix defined outside its registered home):")
        for pfx, f in sorted(out_of_home):
            print(f"  ✗ {pfx}-* defined in {f}; home is {home[pfx]}")
        fail = True
    if new_collisions:
        print("\nID-COLLISIONS (same ID defined in >1 file, not grandfathered):")
        for i, fs in sorted(new_collisions.items()):
            print(f"  ✗ {i} defined in: {', '.join(fs)}")
        fail = True
    repeated = sorted((k, n) for k, n in in_file.items() if n > 1)
    if repeated:
        print("\nID-REPEATED (same ID defined twice in ONE file):")
        for (i, f), n in repeated:
            print(f"  ✗ {i} defined {n}× in {f} — two rows for one id can carry two different "
                  f"requirements, and the later one silently wins")
        fail = True

    # Self-test. Each arm gets a planted break; an arm that cannot fire proves only that the files
    # parsed, which is exactly the state this gate existed in for the whole vocabulary half.
    probe = {}
    _closed_lists({"a": {"enum": ["w", "x", "y", "z"]}, "b": {"enum": ["w", "x", "y", "z"]}},
                  "", probe, "probe.json")
    if len(probe.get(frozenset("wxyz"), [])) != 2:
        print("FAIL [VOC-SELF] the scanner does not see two copies in one document")
        fail = True
    if not _check_projection(frozenset(("a", "b")), "p", "/enum", "registry/taxonomies/action.yaml"):
        print("FAIL [VOC-SELF] VOC-002 cannot detect a drifted projection")
        fail = True
    if not _check_projection(frozenset(("a",)), "p", "/enum", "registry/no-such-file.yaml"):
        print("FAIL [VOC-SELF] VOC-003 cannot detect a missing source")
        fail = True

    if fail:
        print("\nFix: define each rule in its prefix's home only; cite by ID elsewhere. To add a "
              "family, register the prefix first. To resolve a clash, renumber one family to a "
              "disjoint prefix (REL-* -> ERL- precedent). See registry/rule-id-naming.md.")
        return 1

    print("OK — every rule-ID prefix is registered; every ID has a single definition.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

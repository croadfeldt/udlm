#!/usr/bin/env python3
"""Identity-integrity gate (ADR-051): uuid = frozen identity; version under the publish law;
immutable records supersede, never edit.

This gate replaced tests/check_uuid_rotation.py when ADR-051 retired the rotating-uuid
doctrine — the checks inverted: a changed document must now KEEP its uuid and bump its
version. Documents classify into two families by `record_type` (immutable record streams vs
mutable-in-place definitions; docs without a record_type — type specs, providers, profiles,
groups — are mutable). Rule matrix, each rule with an in-memory negative in `--self-test`:

  R1a  mutable doc changed vs base but its uuid moved          -> FAIL (identity is frozen)
  R1b  mutable doc changed vs base but version did not advance -> FAIL (publish law: content
       change => bump >= REVISION; no comparable version on a changed doc is a warning)
  R2   a (handle, version) recorded in the BASE pin manifest resolves to a different digest
       in the working tree                                     -> FAIL (republication refused)
  R3   a declared identity uuid appears more than once         -> FAIL (never shared/reused)
  R4a  immutable record edited in place                        -> FAIL (a change is a NEW
       record: new uuid + `supersedes` naming the predecessor; reusing the file as carrier
       is legal exactly when it does both)
  R4b  immutable record deleted                                -> FAIL (records never vanish)
       ...unless DECLARED in registry/renames.yaml `retired:` (a retirement is stated,
       never silent — the entry names what supersedes it)
  R5   nested provider.uuid / capabilities[].capability_uuid changed -> FAIL (frozen anchors
       accreditations bind to; the provider definition's version must bump instead)
  R6   renamed files are diffed against their base-ref path via registry/renames.yaml (kept
       from the old gate: a rename is never a delete+add, never a gate exemption)
  R7   a document's `$id` encodes a version that disagrees with its `version` field -> FAIL.
       Unlike R1a/R1b this needs no base ref: the document contradicts itself, so it is wrong
       standing still. Two of these sat on main passing every gate — a `$id` says 0.3.0 while
       `version` says 0.3.1 — and a consumer pinning by `$id` resolves a version the record
       does not claim to be.

Scope: every registry/**/*.{json,yaml} document. Multi-document YAML streams are handled
per-document (load_all — the old gate's single-doc load was a latent bug). New files are
exempt from the change rules (nothing to diff) but join the R3 uniqueness set.
Doctrine: registry/VERSIONING.md § "Identity, version, digest"; docs/adr/ADR-051.
"""
import glob
import importlib.util
import os
import subprocess
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.environ.get("IDENTITY_GATE_BASE", os.environ.get("UUID_GATE_BASE", "origin/main"))

# Shared canonicalization + parsing live in the pin-manifest tool (single source).
_spec = importlib.util.spec_from_file_location(
    "generate_pin_manifest", os.path.join(ROOT, "registry", "tools", "generate_pin_manifest.py"))
_pin = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pin)

IMMUTABLE_RECORD_TYPES = {
    "decision_record", "layer", "audit_record", "audit_leaf", "commit_log_entry",
    "accreditation", "regeneration_manifest", "finding_routing_record",
}
KNOWN_MUTABLE_RECORD_TYPES = {"policy", "catalog_item"}


def classify(doc, warns=None, rel=""):
    """'immutable' | 'mutable'. Unknown instance record_type => mutable + warning."""
    rt = doc.get("record_type")
    if rt in IMMUTABLE_RECORD_TYPES:
        return "immutable"
    if rt is not None and rt not in KNOWN_MUTABLE_RECORD_TYPES and warns is not None:
        warns.append(f"{rel}: unknown record_type {rt!r} — classified mutable; register it "
                     f"in tests/check_identity_integrity.py if that is wrong")
    return "mutable"


def _semver(v):
    try:
        return tuple(int(p) for p in str(v).split("."))
    except ValueError:
        return None


def _supersedes(doc):
    """The predecessor uuid set a record declares, across the carrier fields in use."""
    out = set()
    s = doc.get("supersedes")
    if isinstance(s, str):
        out.add(s)
    elif isinstance(s, list):
        out.update(x for x in s if isinstance(x, str))
    res = doc.get("resolution")
    if isinstance(res, dict) and isinstance(res.get("supersedes_finding_uuid"), str):
        out.add(res["supersedes_finding_uuid"])
    return out


def _identity_view(doc):
    """The doc as it counts for identity — non-normative documentation surfaces stripped (ADR-051:
    top-level `coverage`, and the `spec.examples` JSON Schema annotation, ADR-055), so a
    docs-only edit is not a content change and does not oblige a version bump. Shares the exact
    strip the digest uses, so R1b and the digest agree on what identity covers."""
    return _pin._strip_nonnormative(doc) if isinstance(doc, dict) else doc


def check_pair(rel, old_doc, new_doc, fails, warns):
    """Family rules for one (base, working) document pair from the same file."""
    if _identity_view(old_doc) == _identity_view(new_doc):
        return
    family = classify(new_doc, warns, rel)
    old_uuid, new_uuid = old_doc.get("uuid"), new_doc.get("uuid")

    if family == "immutable":
        if old_uuid is not None and old_uuid != new_uuid and old_uuid in _supersedes(new_doc):
            return  # a NEW record superseding the old one, carried in the same file — legal
        fails.append(f"{rel}: R4a immutable record ({new_doc.get('record_type')}) edited in "
                     f"place — a change is a NEW record: mint a new uuid and name "
                     f"{old_uuid or 'the predecessor'} in `supersedes`; published records "
                     f"are never edited (ADR-051 family rule)")
        return

    if old_uuid is not None and old_uuid != new_uuid:
        fails.append(f"{rel}: R1a uuid changed on a mutable document "
                     f"({old_uuid} -> {new_uuid}) — the uuid is frozen identity (ADR-051); "
                     f"content changes bump the version, never the uuid")
    old_v, new_v = _semver(old_doc.get("version")), _semver(new_doc.get("version"))
    if old_v is None or new_v is None:
        if "$schema" in new_doc or "$schema" in old_doc:
            return  # SPEC-axis meta-schema: versioned by the spec axis, edited in place,
                    # logged in VERSIONING.md's pre-1.0 surface-change log — not per-doc semver
        warns.append(f"{rel}: changed document carries no comparable `version` — the publish "
                     f"law (content change => bump) cannot be verified here")
    elif new_v <= old_v:
        fails.append(f"{rel}: R1b content changed but version did not advance "
                     f"({old_doc.get('version')} -> {new_doc.get('version')}) — publish law: "
                     f"any content change ships a bump (>= REVISION)")


def check_provider(rel, old_doc, new_doc, fails):
    """R5: nested provider/capability identities are frozen; the definition version bumps."""
    if old_doc == new_doc:
        return
    old_p, new_p = old_doc.get("provider") or {}, new_doc.get("provider") or {}
    if old_p.get("uuid") and old_p.get("uuid") != new_p.get("uuid"):
        fails.append(f"{rel}: R5 provider.uuid changed ({old_p.get('uuid')} -> "
                     f"{new_p.get('uuid')}) — a provider's identity is the frozen anchor its "
                     f"accreditations bind to (ADR-051); bump provider.version instead")
    old_caps = {c.get("name") or f"#{i}": c
                for i, c in enumerate(old_doc.get("capabilities") or [])}
    for i, cap in enumerate(new_doc.get("capabilities") or []):
        prev = old_caps.get(cap.get("name") or f"#{i}")
        if prev and prev.get("capability_uuid") and \
                prev["capability_uuid"] != cap.get("capability_uuid"):
            fails.append(f"{rel}: R5 capability_uuid changed on capability "
                         f"{cap.get('name') or i} — capability identity is frozen (ADR-051); "
                         f"a surface change bumps the capability version")
    if old_p and new_p and old_p.get("uuid") == new_p.get("uuid"):
        old_v, new_v = _semver(old_p.get("version")), _semver(new_p.get("version"))
        if old_v is not None and new_v is not None and new_v <= old_v:
            fails.append(f"{rel}: R1b provider definition changed but provider.version did "
                         f"not advance ({old_p.get('version')} -> {new_p.get('version')}) — "
                         f"publish law (ADR-045 §8 / ADR-051)")


def check_base_manifest(base_manifest, rows, fails):
    """R2: a (handle, version) the base manifest already recorded must resolve to the same
    digest in the working tree — republication with different bytes is refused."""
    for handle, version, dig, rel in rows:
        entry = base_manifest.get(handle)
        if not entry:
            continue
        recorded = (entry.get("versions") or {}).get(version)
        if recorded is not None and recorded != dig:
            fails.append(f"{rel}: R2 {handle}@{version} republished with different bytes "
                         f"(recorded {recorded}, working tree {dig}) — a published "
                         f"(identity, version) is immutable; bump the version")


def _renames():
    """new_path -> old_path, from registry/renames.yaml (R6, the rename-map discipline: every
    path rename ships with an explicit old->new map). A renamed file is the SAME entity as
    its base-ref path — it is diffed against that path, never silently exempted as 'new'."""
    p = os.path.join(ROOT, "registry", "renames.yaml")
    if not os.path.exists(p):
        return {}
    doc = yaml.safe_load(open(p, encoding="utf-8")) or {}
    return {new: old for old, new in (doc.get("renames") or {}).items()}


def _git_show(rel):
    r = subprocess.run(["git", "-C", ROOT, "show", f"{BASE}:{rel}"],
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def _parse(text, path):
    try:
        return _pin.parse_documents(text, path)
    except Exception:
        return []


def pair_documents(old_docs, new_docs):
    """Match documents of one file across base/working: by uuid first, then positionally
    among the unmatched (so a rotated uuid still pairs and is caught, not exempted).
    Returns (pairs, unmatched_old, unmatched_new)."""
    new_by_uuid = {d["uuid"]: d for d in new_docs if d.get("uuid")}
    pairs, unmatched_old, used = [], [], set()
    for od in old_docs:
        u = od.get("uuid")
        if u and u in new_by_uuid:
            pairs.append((od, new_by_uuid[u]))
            used.add(id(new_by_uuid[u]))
        else:
            unmatched_old.append(od)
    unmatched_new = [d for d in new_docs if id(d) not in used]
    while unmatched_old and unmatched_new:
        pairs.append((unmatched_old.pop(0), unmatched_new.pop(0)))
    return pairs, unmatched_old, unmatched_new


def _retired_paths():
    """Paths declared retired in registry/renames.yaml `retired:` — a removal that is STATED,
    with the entry naming what supersedes it. Silent deletion still fails R4b."""
    p = os.path.join(ROOT, "registry", "renames.yaml")
    if not os.path.exists(p):
        return set()
    try:
        import yaml
        doc = yaml.safe_load(open(p)) or {}
    except Exception:
        return set()
    return set((doc.get("retired") or {}).keys())


def check_file(rel, old_docs, new_docs, fails, warns):
    pairs, gone, _new = pair_documents(old_docs, new_docs)
    for od, nd in pairs:
        check_pair(rel, od, nd, fails, warns)
        if isinstance(od.get("provider"), dict) or isinstance(nd.get("provider"), dict):
            check_provider(rel, od, nd, fails)
    superseders = set()
    for d in new_docs:
        superseders |= _supersedes(d)
    for od in gone:
        if classify(od) == "immutable" and od.get("uuid") not in superseders:
            fails.append(f"{rel}: R4b immutable record ({od.get('record_type')} "
                         f"{od.get('handle') or od.get('name') or od.get('uuid')}) deleted — "
                         f"published records never vanish; supersede instead (ADR-051)")


def check_id_version_agreement(doc, rel, fails):
    """R7 — a record must not contradict itself about which version it is.

    `$id` ends in the version (…/class/Compute.VM/0.12.0) and `version` states it too. Nothing
    compared them, so a bump that missed the `$id` produced a record claiming two versions at once,
    with every gate green. A consumer pinning by `$id` — which is what `$id` is for — then resolves
    a version the record does not claim to be.

    Base-ref-free by design: this is an internal contradiction, so it is a defect standing still
    rather than only across a change."""
    sid, ver = doc.get("$id"), doc.get("version")
    if not isinstance(sid, str) or not isinstance(ver, str):
        return
    tail = sid.rsplit("/", 1)[-1]
    if not _semver(tail):
        return                      # a $id that does not end in a version encodes nothing to disagree
    if tail != ver:
        fails.append(f"{rel}: R7 $id ends /{tail} but version is {ver} — the record contradicts "
                     f"itself, and a consumer pinning by $id resolves a version it does not claim")


def _identity_uuids(doc, rel):
    """The uuids a document DECLARES as identity (not references): its own, its provider's,
    and its capabilities' (the nested-uuid hole the old gate missed)."""
    out = []
    if isinstance(doc.get("uuid"), str):
        out.append((doc["uuid"], rel))
    p = doc.get("provider")
    if isinstance(p, dict) and isinstance(p.get("uuid"), str):
        out.append((p["uuid"], f"{rel} (provider)"))
    for c in doc.get("capabilities") or []:
        if isinstance(c, dict) and isinstance(c.get("capability_uuid"), str):
            out.append((c["capability_uuid"], f"{rel} (capability {c.get('name')})"))
    return out


def _base_resolves():
    """The base ref must resolve to a commit, or the whole diff is against an empty tree and
    every file reads as 'new' — a silent pass. Fail CLOSED: an unresolvable base is an error,
    not a green (the 2026-07-28 sweep's AG1/N-02 finding)."""
    return subprocess.run(["git", "-C", ROOT, "rev-parse", "--verify", "--quiet",
                           f"{BASE}^{{commit}}"], capture_output=True, text=True).returncode == 0


def main():
    if "--self-test" in sys.argv:
        return self_test()

    if not _base_resolves():
        print(f"ERROR: base ref {BASE!r} does not resolve to a commit — cannot verify identity "
              f"integrity. Fetch it (CI needs fetch-depth: 0) or set IDENTITY_GATE_BASE. "
              f"Refusing to pass vacuously (fail-closed).", file=sys.stderr)
        return 2

    fails, warns = [], []
    renamed = _renames()
    seen = {}          # identity uuid -> where declared (R3)
    current_files = {}  # rel -> parsed docs

    paths = sorted(glob.glob(os.path.join(ROOT, "registry", "**", "*.json"), recursive=True) +
                   glob.glob(os.path.join(ROOT, "registry", "**", "*.yaml"), recursive=True))
    for p in paths:
        rel = os.path.relpath(p, ROOT)
        # Generated artifacts (registry/generated/*) are compiled projections of Class sources, not
        # authored records — they carry their source Class's identity by construction and regenerate
        # deterministically (gated by generate_class_specs.py --check), so they hold no independent
        # authored identity here (else the compiled spec would R3-duplicate its source Class).
        if (os.sep + "generated" + os.sep) in (os.sep + rel + os.sep):
            continue
        docs = _parse(open(p, encoding="utf-8").read(), p)
        current_files[rel] = docs
        for d in docs:
            check_id_version_agreement(d, rel, fails)      # R7 — needs no base ref
            for u, where in _identity_uuids(d, rel):
                if u in seen:
                    fails.append(f"{where}: R3 uuid {u[:13]}… duplicates {seen[u]} — an "
                                 f"identity is never shared or reused")
                else:
                    seen[u] = where

    checked = 0
    for rel, docs in current_files.items():
        old_text = _git_show(rel)
        if old_text is None and rel in renamed:
            old_text = _git_show(renamed[rel])  # R6: same entity as its base-ref path
        if old_text is None:
            continue  # new file — uniqueness already checked
        checked += 1
        check_file(rel, _parse(old_text, rel), docs, fails, warns)

    # R4b for whole deleted files (a rename is not a deletion — R6)
    r = subprocess.run(["git", "-C", ROOT, "ls-tree", "-r", "--name-only", BASE, "registry/"],
                       capture_output=True, text=True)
    if r.returncode == 0:
        renamed_old = set(renamed.values()) | _retired_paths()
        for rel in r.stdout.splitlines():
            if not rel.endswith((".json", ".yaml")) or rel in current_files or rel in renamed_old:
                continue
            check_file(rel, _parse(_git_show(rel) or "", rel), [], fails, warns)

    # R2 against the base pin manifest
    base_manifest = _pin.base_manifest()
    if base_manifest:
        check_base_manifest(base_manifest, _pin.tree_rows(), fails)

    for w in warns:
        print("WARN", w)
    for f in fails:
        print("FAIL", f)
    print(f"\n{checked} document file(s) diffed vs {BASE}; {len(seen)} identity uuid(s); "
          f"{len(fails)} violation(s), {len(warns)} warning(s)")
    return 1 if fails else 0


def self_test():
    """Every rule's negative, in memory — no git, no tree."""
    results = []

    def report(name, ok, extra=""):
        results.append((name, ok))
        print(("  ok   " if ok else "  FAIL ") + name + (extra if not ok else ""))

    def case(name, fails, expect_rule):
        report(name, any(f" {expect_rule} " in f for f in fails), f" — got {fails!r}")

    def clean(name, fails):
        report(name, not fails, f" — unexpected: {fails!r}")

    U1, U2 = "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222"

    # R7 — a record contradicting itself about its own version. Needs no base ref, so it is
    # checked here on a bare document rather than a pair.
    _f = []
    check_id_version_agreement(
        {"$id": "https://udlm.dev/registry/udlm/0.1/class/Probe.Type/0.3.0", "version": "0.3.1"},
        "probe", _f)
    case("R7 $id version disagrees with the version field", _f, "R7")
    _f = []
    check_id_version_agreement(
        {"$id": "https://udlm.dev/registry/udlm/0.1/class/Probe.Type/0.3.1", "version": "0.3.1"},
        "probe", _f)
    clean("R7 agreeing $id and version pass", _f)
    _f = []
    check_id_version_agreement({"$id": "https://udlm.dev/registry/udlm/0.1/no-version-tail",
                                "version": "0.3.1"}, "probe", _f)
    clean("R7 a $id with no version tail encodes nothing to disagree", _f)
    U3 = "33333333-3333-4333-8333-333333333333"

    # R1a — mutable changed + uuid moved
    f, w = [], []
    check_pair("x.yaml", {"uuid": U1, "version": "1.0.0", "a": 1},
               {"uuid": U2, "version": "1.0.1", "a": 2}, f, w)
    case("R1a mutable uuid rotation refused", f, "R1a")

    # R1b — mutable changed + version stalled
    f, w = [], []
    check_pair("x.yaml", {"uuid": U1, "version": "1.0.0", "a": 1},
               {"uuid": U1, "version": "1.0.0", "a": 2}, f, w)
    case("R1b unbumped version refused", f, "R1b")

    # legal mutable change — uuid kept, version bumped
    f, w = [], []
    check_pair("x.yaml", {"uuid": U1, "version": "1.0.0", "a": 1},
               {"uuid": U1, "version": "1.0.1", "a": 2}, f, w)
    clean("legal mutable edit passes (uuid frozen, version bumped)", f)

    # R2 — republication against the base manifest
    f = []
    check_base_manifest(
        {"type:Example.Thing": {"versions": {"1.0.0": "sha256:" + "a" * 64}}},
        [("type:Example.Thing", "1.0.0", "sha256:" + "b" * 64, "x.yaml")], f)
    case("R2 republication with different bytes refused", f, "R2")
    f = []
    check_base_manifest(
        {"type:Example.Thing": {"versions": {"1.0.0": "sha256:" + "a" * 64}}},
        [("type:Example.Thing", "1.0.1", "sha256:" + "b" * 64, "x.yaml")], f)
    clean("R2 new version beside a recorded row passes", f)

    # R3 — duplicated identity uuid (the seen-set logic, exercised directly)
    seen, f = {}, []
    for doc, rel in [({"uuid": U1}, "a.yaml"),
                     ({"provider": {"uuid": U1, "version": "1.0.0"}}, "b.json")]:
        for u, where in _identity_uuids(doc, rel):
            if u in seen:
                f.append(f"{where}: R3 uuid {u[:13]}… duplicates {seen[u]}")
            seen[u] = where
    case("R3 shared identity refused (incl. nested provider uuid)", f, "R3")

    # R4a — immutable edited in place / replaced without supersede
    f, w = [], []
    check_pair("x.yaml", {"record_type": "layer", "uuid": U1, "version": "1.0.0", "a": 1},
               {"record_type": "layer", "uuid": U1, "version": "1.0.1", "a": 2}, f, w)
    case("R4a immutable in-place edit refused", f, "R4a")
    f, w = [], []
    check_pair("x.yaml", {"record_type": "layer", "uuid": U1, "version": "1.0.0", "a": 1},
               {"record_type": "layer", "uuid": U2, "version": "2.0.0", "a": 2}, f, w)
    case("R4a replacement without supersedes refused", f, "R4a")
    f, w = [], []
    check_pair("x.yaml", {"record_type": "layer", "uuid": U1, "version": "1.0.0", "a": 1},
               {"record_type": "layer", "uuid": U2, "version": "2.0.0", "a": 2,
                "supersedes": [U1]}, f, w)
    clean("legal supersede in the same carrier file passes", f)

    # R4b — immutable record deleted
    f, w = [], []
    check_file("x.yaml", [{"record_type": "layer", "uuid": U1, "version": "1.0.0"}], [], f, w)
    case("R4b immutable deletion refused", f, "R4b")

    # R5 — nested provider / capability identity moved
    f = []
    check_provider("p.json", {"provider": {"uuid": U1, "version": "1.0.0"}},
                   {"provider": {"uuid": U2, "version": "1.0.1"}}, f)
    case("R5 provider.uuid change refused", f, "R5")
    f = []
    check_provider("p.json",
                   {"provider": {"uuid": U1, "version": "1.0.0"},
                    "capabilities": [{"name": "compute", "capability_uuid": U1}]},
                   {"provider": {"uuid": U1, "version": "1.0.1"},
                    "capabilities": [{"name": "compute", "capability_uuid": U2}]}, f)
    case("R5 capability_uuid change refused", f, "R5")
    f = []
    check_provider("p.json", {"provider": {"uuid": U1, "version": "1.0.0"}, "a": 1},
                   {"provider": {"uuid": U1, "version": "1.0.0"}, "a": 2}, f)
    case("R1b provider version stall refused", f, "R1b")

    # R6 — the rename map routes a moved file to its base path, and the pair check still
    # fires across the rename (a rename is never an exemption)
    ren = {"registry/new.yaml": "registry/old.yaml"}
    routed = ren.get("registry/new.yaml")
    f, w = [], []
    check_pair(routed, {"uuid": U1, "version": "1.0.0", "a": 1},
               {"uuid": U1, "version": "1.0.0", "a": 2}, f, w)
    report("R6 rename resolves to base path and is not exempt",
           routed == "registry/old.yaml" and any(" R1b " in x for x in f))

    # multi-doc pairing: a rotated uuid inside a `---` stream still pairs positionally (the
    # old gate's single-document load was a latent bug; per-document pairing closes it)
    pairs, gone, new = pair_documents(
        [{"uuid": U1, "version": "1.0.0", "a": 1}, {"uuid": U2, "version": "1.0.0", "b": 1}],
        [{"uuid": U1, "version": "1.0.0", "a": 1}, {"uuid": U3, "version": "1.0.0", "b": 2}])
    report("multi-doc streams pair per document", len(pairs) == 2 and not gone and not new)

    # fail-closed: an unresolvable base ref must ERROR (exit 2), never pass vacuously.
    probe = subprocess.run(
        [sys.executable, os.path.abspath(__file__)],
        cwd=ROOT, capture_output=True, text=True,
        env={**os.environ, "IDENTITY_GATE_BASE": "refs/nonexistent/base-probe-zzz"})
    report("fail-closed on unresolvable base ref (exit 2, not vacuous 0)", probe.returncode == 2)

    failed = [n for n, ok in results if not ok]
    print(f"\nidentity-integrity self-test: {len(results)} case(s), {len(failed)} failure(s)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

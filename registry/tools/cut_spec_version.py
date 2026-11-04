#!/usr/bin/env python3
"""The spec re-stamp that cuts a release: `udlm/<from>` → `udlm/<to>` (VERSIONING.md, the cut procedure).

Dry run by default: prints what the cut would touch and stops. `--apply` does it. Nothing here tags
anything; the tag is the maintainer's act, on the maintainer's go (row 127 ruling 6; WP9).

What `--apply` does, in order:
  1. Re-stamps `conforms_to` and every `$id` / `type_ref` spec segment in the registry and the
     normative documents. Records in docs/adr, docs/dr and docs/research keep their wording; the
     law (VERSIONING.md), the two scope documents and README.md are edited by hand afterwards.
  2. Bumps every class's REVISION: a class whose bytes change ships a new version (publish law,
     R1b/R2), and a re-stamp changes the bytes.
  3. Re-issues every immutable example record the re-stamp changes, never editing it in place
     (ADR-051). A state record gets a new v7 id, `supersedes` the old, and is resealed with
     `previous` = the old head. A record with `uuid` + `version` + `supersedes` (decision record,
     layer, vocabulary term, regeneration manifest, finding-routing record) gets a new uuid,
     `supersedes`, and a REVISION bump. Every reference to a re-issued id — `intent_ref`,
     `requested_ref`, `root_request_uuid`, `caused_by_request`, `*_ref_head`, must-reject cases —
     is repointed. Kinds with an identity but no `supersedes` (accreditation, composition, policy,
     profile, promotion evidence, registration verdict, log checkpoint, the class example) are
     listed in the dry run; they are re-stamped in place and the cut row says so, or the
     maintainer rules otherwise before the cut.
  4. Regenerates the served specs, the catalog, the pin manifest and the health report.
  Then the operator runs every validate.yml step, refreshes the readability and doc-example
  baselines once they report 0 new, and makes the hand edits. The cut is one PR; the tag follows.

Usage:  python3 registry/tools/cut_spec_version.py --from 0.1 --to 1.0 [--apply]
"""
import argparse
import datetime
import glob
import os
import re
import subprocess
import sys
import uuid

import yaml

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "registry", "tools"))

RECORD_FILES = ("registry/**/*.yaml", "registry/**/*.json")
DOC_FILES = ("docs/spec/**/*.md", "CONFORMANCE.md", "GLOSSARY.md", "registry/*.md")
SKIP = ("registry/generated/", "registry/pin-manifest.json", "docs/adr/", "docs/dr/", "docs/research/",
        "registry/VERSIONING.md", "registry/UDLM-0.1-SCOPE.md", "registry/UDLM-1.0-LOCKDOWN.md")
REISSUE_BY_VERSION = {"decision_record", "vocabulary_term", "regeneration_manifest", "finding_routing_record"}  # new uuid, supersedes, REVISION
APPEND_VERSION = {"layer"}            # immutable and pinned by version: the new version is appended, the old one stays
BUMP_IN_PLACE = {"policy", "profile", "class", "provider_registration"}  # versioned, same identity: REVISION bump
NEW_IDENTITY = {"accreditation"}  # append-only: new identity (+ REVISION where versioned)
MUTABLE = {"composition", "conformance_declaration", "log_checkpoint", "promotion_evidence", "registration_verdict"}  # the uuid is frozen identity; re-stamped in place
SUPERSEDES_IS_STRING = {"finding_routing_record", "regeneration_manifest"}
REF_KEYS = ("intent_ref", "requested_ref", "root_request_uuid", "caused_by_request", "realized_ref", "record_ref")


def files(patterns):
    out = set()
    for p in patterns:
        out.update(glob.glob(os.path.join(REPO, p), recursive=True))
    return sorted(f for f in out if not any(s in os.path.relpath(f, REPO) for s in SKIP))


def hits(token, paths):
    out = {}
    for f in paths:
        try:
            n = open(f, encoding="utf-8").read().count(token)
        except UnicodeDecodeError:
            continue
        if n:
            out[os.path.relpath(f, REPO)] = n
    return out


def grouped(h):
    g = {}
    for rel, n in h.items():
        parts = rel.split("/")
        key = "/".join(parts[:2]) if len(parts) > 2 else rel
        g[key] = g.get(key, 0) + n
    return dict(sorted(g.items(), key=lambda kv: -kv[1]))


def example_kinds(token):
    kinds = {}
    for f in glob.glob(os.path.join(REPO, "registry", "examples", "**", "*.yaml"), recursive=True):
        text = open(f, encoding="utf-8").read()
        if token not in text:
            continue
        for doc in text.split("\n---\n"):
            if token not in doc:
                continue
            try:
                d = yaml.safe_load(doc)
            except Exception:
                continue
            if isinstance(d, dict) and d.get("record_type"):
                kinds.setdefault(d["record_type"], 0)
                kinds[d["record_type"]] += 1
    return kinds


def bump_revision(text):
    v = re.search(r"^version: (\d+)\.(\d+)\.(\d+)$", text, re.M)
    if not v:
        return text
    nv = f"{v.group(1)}.{v.group(2)}.{int(v.group(3)) + 1}"
    text = text.replace(v.group(0), f"version: {nv}", 1)
    return re.sub(r"(/class/[A-Za-z.]+/)\d+\.\d+\.\d+", rf"\g<1>{nv}", text)


def new_v7(n):
    base = int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)
    h = f"{base + n:012x}"
    return f"{h[:8]}-{h[8:12]}-7{n:03x}-8{n:03x}-{n:012x}"


def add_supersedes(doc, idkey, old, scalar=False):
    """Replace a top-level `supersedes` block with the one old id, or add one after the id line."""
    lines = doc.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("supersedes:"):
            j = i + 1
            while j < len(lines) and re.match(r"^\s*- ", lines[j]):
                j += 1
            lines[i:j] = [f"supersedes: {old}"] if scalar else ["supersedes:", f"  - {old}"]
            return "\n".join(lines)
    for i, line in enumerate(lines):
        if line.startswith(f"{idkey}: "):
            lines[i:i + 1] = [line, f"supersedes: {old}"] if scalar else [line, "supersedes:", f"  - {old}"]
            return "\n".join(lines)
    return doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="src", required=True)
    ap.add_argument("--to", dest="dst", required=True)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    old_token, new_token = f"udlm/{a.src}", f"udlm/{a.dst}"

    rec = hits(old_token, files(RECORD_FILES))
    doc = hits(old_token, files(DOC_FILES))
    kinds = example_kinds(old_token)
    classes = sorted(glob.glob(os.path.join(REPO, "registry", "classes", "**", "*.yaml"), recursive=True))
    print(f"cut {old_token} -> {new_token}: {'APPLYING' if a.apply else 'dry run'}")
    print(f"  registry files re-stamped: {len(rec)} ({sum(rec.values())} occurrences)")
    for k, n in grouped(rec).items():
        print(f"    {k}: {n}")
    print(f"  documents re-stamped: {len(doc)} ({sum(doc.values())} occurrences); by hand afterwards: VERSIONING.md, README.md, CONFORMANCE.md line 3")
    print(f"  classes bumped (REVISION): {len(classes)}")
    print("  example records re-issued, never edited in place:")
    for rt, n in sorted(kinds.items()):
        how = ("new v7 id, supersedes, resealed" if rt.endswith("_record") and rt != "finding_routing_record"
               else "new uuid, supersedes, REVISION bump" if rt in REISSUE_BY_VERSION
               else "new version appended, the old one stays (pinned by version)" if rt in APPEND_VERSION
               else "REVISION bump, same identity" if rt in BUMP_IN_PLACE
               else "new identity and REVISION (append-only kind)" if rt in NEW_IDENTITY
               else "re-stamped in place (a mutable document, or no identity)")
        print(f"    {rt}: {n} — {how}")
    if not a.apply:
        return 0

    # 1. re-stamp documents and non-example registry files
    for rel in list(rec) + list(doc):
        if rel.startswith("registry/examples/"):
            continue
        p = os.path.join(REPO, rel)
        text = open(p, encoding="utf-8").read()
        open(p, "w", encoding="utf-8").write(text.replace(old_token, new_token))
    # 2. every class ships a new REVISION
    for f in classes:
        text = open(f, encoding="utf-8").read()
        open(f, "w", encoding="utf-8").write(bump_revision(text))

    # 3. re-issue example records
    import integrity_chain as ic
    paths = sorted(glob.glob(os.path.join(REPO, "registry", "examples", "**", "*.yaml"), recursive=True))
    texts = {p: open(p, encoding="utf-8").read().split("\n---\n") for p in paths}
    idmap, n = {}, 0
    for p, docs in texts.items():
        for i, d_text in enumerate(docs):
            if old_token not in d_text:
                continue
            try:
                d = yaml.safe_load(d_text)
            except Exception:
                docs[i] = d_text.replace(old_token, new_token)
                continue
            if not isinstance(d, dict):
                docs[i] = d_text.replace(old_token, new_token)
                continue
            rt = d.get("record_type", "")
            t = d_text.replace(old_token, new_token)
            if rt.endswith("_record") and rt != "finding_routing_record" and "record_uuid" in d:
                old = d["record_uuid"]
                idmap[old] = new_v7(n); n += 1
                t = re.sub(r"^record_uuid: \S+$", f"record_uuid: {idmap[old]}", t, count=1, flags=re.M)
                t = add_supersedes(t, "record_uuid", old)
            elif rt in REISSUE_BY_VERSION and "uuid" in d:
                old = d["uuid"]
                idmap[old] = str(uuid.uuid4())
                t = re.sub(r"^uuid: \S+$", f"uuid: {idmap[old]}", t, count=1, flags=re.M)
                t = add_supersedes(t, "uuid", old, scalar=rt in SUPERSEDES_IS_STRING)
                t = bump_revision(t)
            elif rt in APPEND_VERSION and "uuid" in d:
                old = d["uuid"]
                new = str(uuid.uuid4())
                t = re.sub(r"^uuid: \S+$", f"uuid: {new}", t, count=1, flags=re.M)
                t = add_supersedes(t, "uuid", old)
                t = bump_revision(t)
                # the old version stays, in its own file, so pins and lineage still resolve to it;
                # the new version gets a sibling file, as the repo's own v2 examples do
                ver = re.search(r"^version: (\S+)$", t, re.M).group(1)
                sibling = re.sub(r"\.yaml$", f"-{ver}.yaml", p)
                open(sibling, "w", encoding="utf-8").write(t if t.endswith("\n") else t + "\n")
                t = d_text                      # the original document is left exactly as it was
            elif rt in BUMP_IN_PLACE:
                t = bump_revision(t)
            elif rt in NEW_IDENTITY and "uuid" in d:
                old = d["uuid"]
                idmap[old] = str(uuid.uuid4())
                t = re.sub(r"^uuid: \S+$", f"uuid: {idmap[old]}", t, count=1, flags=re.M)
                t = bump_revision(t)
            docs[i] = t
    # repoint every reference to a re-issued id, then reseal in dependency order
    for p, docs in texts.items():
        for i, t in enumerate(docs):
            for k in REF_KEYS:
                t = re.sub(rf"^(\s*{k}: )(\S+)$", lambda m: m.group(1) + idmap.get(m.group(2), m.group(2)), t, flags=re.M)
            # repoint every other mention of a re-issued id, but never a `supersedes` value: that is the old id on purpose
            out_lines, in_sup = [], False
            for line in t.split("\n"):
                if line.startswith("supersedes:"):
                    in_sup = line.strip() == "supersedes:"
                    out_lines.append(line)
                    continue
                if in_sup and re.match(r"^\s*- ", line):
                    out_lines.append(line)
                    continue
                in_sup = False
                for old, new in idmap.items():
                    if old in line:
                        line = line.replace(old, new)
                out_lines.append(line)
            docs[i] = "\n".join(out_lines)
    heads = {}
    order = {"Intent": 0, "Requested": 1, "Realized": 2, "Discovered": 3}
    sealed = []
    for p, docs in texts.items():
        for i, t in enumerate(docs):
            if re.search(r"^integrity:\n", t, re.M) and re.search(r"^record_uuid: ", t, re.M):
                st = re.search(r"^state: (\w+)$", t, re.M)
                sealed.append((order.get(st.group(1) if st else "Intent", 0), p, i))
    for _, p, i in sorted(sealed, key=lambda x: x[0]):
        t = texts[p][i]
        for k, rk in (("intent_ref_head", "intent_ref"), ("requested_ref_head", "requested_ref")):
            m = re.search(rf"^{rk}: (\S+)$", t, re.M)
            if m and m.group(1) in heads and re.search(rf"^{k}: ", t, re.M):
                t = re.sub(rf"^{k}: \S+$", f"{k}: {heads[m.group(1)]}", t, count=1, flags=re.M)
        old_head = re.search(r"^  head: (\S+)$", t, re.M).group(1)
        d = yaml.safe_load(t)
        d.pop("integrity")
        new_head = ic.seal(d, previous=old_head)["integrity"]["head"]
        t = re.sub(r"^  head: \S+$", f"  head: {new_head}", t, count=1, flags=re.M)
        if re.search(r"^  previous: ", t, re.M):
            t = re.sub(r"^  previous: \S+$", f"  previous: {old_head}", t, count=1, flags=re.M)
        else:
            t = re.sub(r"^(  head: .*)$", rf"\1\n  previous: {old_head}", t, count=1, flags=re.M)
        heads[re.search(r"^record_uuid: (\S+)$", t, re.M).group(1)] = new_head
        texts[p][i] = t
    for p, docs in texts.items():
        new = "\n---\n".join(docs)
        if new != open(p, encoding="utf-8").read():
            open(p, "w", encoding="utf-8").write(new)

    # 3b. must-reject cases that pin a class version: repin to the version now served
    served = {}
    for f in classes:
        d = yaml.safe_load(open(f, encoding="utf-8"))
        served[d["resource_type"]] = str(d["version"])
    for f in glob.glob(os.path.join(REPO, "registry", "examples", "must-reject", "*.yaml")):
        t = open(f, encoding="utf-8").read()
        rt = re.search(r"^\s*resource_type: (\S+)$", t, re.M)
        if rt and rt.group(1) in served:
            t2 = re.sub(r"^(\s*type_version: )\S+$", rf"\g<1>{served[rt.group(1)]}", t, count=1, flags=re.M)
            t2 = re.sub(rf"(/{re.escape(rt.group(1))}/)\d+\.\d+\.\d+", rf"\g<1>{served[rt.group(1)]}", t2)
            if t2 != t:
                open(f, "w", encoding="utf-8").write(t2)
    # 4. regenerate
    for tool in ("generate_class_specs", "generate_type_catalog", "generate_pin_manifest"):
        subprocess.run([sys.executable, os.path.join(REPO, "registry", "tools", tool + ".py")], capture_output=True)
    for tool in ("spec_coverage", "model_health"):
        subprocess.run([sys.executable, os.path.join(REPO, "tests", tool + ".py")], capture_output=True)
    print(f"applied: {len(idmap)} record(s) re-issued or re-identified, {len(classes)} class(es) bumped. Now: every validate.yml step; rebuild any must-reject case that embeds a head of a re-issued record; baselines at 0 new; the hand edits.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

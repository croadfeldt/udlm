#!/usr/bin/env python3
"""The decisions register: one file per ruling, rendered into one table.

Every ruling is a file under docs/adr/register/, named by its number (`161.md`) or its name
(`ADR-PROV-001.md`). Two pull requests that add two rulings add two files and never conflict;
the one shared file, docs/adr/README.md, is rendered from them and refreshed in its own small
pull request after a merge round.

A row file is a front-matter block and one line of body, the table cell verbatim:

    ---
    id: 161
    link: ADR-161-something.md        # optional: the ADR prose file the number links to
    order: 62.5                       # optional: where a named ruling sorts among the numbers
    ---
    **Title.** The body, one paragraph, under 150 words.

  render_register.py            rewrite the README's table from the files (newest on top)
  render_register.py --check    REG-001 every file is named by its id and has one body line;
                                REG-002 ids are unique; REG-003 the README holds no row that
                                has no file and no row whose text differs from its file; rows
                                that exist as files but are not in the README yet are PENDING:
                                reported, never failed, so main stays green between a merge and
                                the refresh pull request that renders them.
  render_register.py --check --strict   also fails on pending rows: the refresh pull request's
                                own proof that it rendered everything.
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REGDIR = os.path.join(ROOT, "docs", "adr", "register")
README = os.path.join(ROOT, "docs", "adr", "README.md")
START, END = "<!-- register:rows:start -->", "<!-- register:rows:end -->"
ROW = re.compile(r"^\|\s*(?:\[(?P<lid>[^\]]+)\]\((?P<link>[^)]+)\)|(?P<id>[^|\s]+))\s*\|(?P<rest>.*)\|\s*$")


def load():
    rows, fails = [], []
    for p in sorted(glob.glob(os.path.join(REGDIR, "*.md"))):
        name = os.path.basename(p)[:-3]
        text = open(p, encoding="utf-8").read()
        m = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
        if not m:
            fails.append(f"REG-001 {name}: no front matter")
            continue
        meta = dict(l.split(":", 1) for l in m.group(1).splitlines() if ":" in l)
        meta = {k.strip(): v.strip() for k, v in meta.items()}
        body = m.group(2).strip("\n")
        if "\n" in body or not body:
            fails.append(f"REG-001 {name}: the body must be exactly one non-empty line (the table cell)")
        if meta.get("id") != name:
            fails.append(f"REG-001 {name}: id {meta.get('id')!r} must equal the file name")
        rows.append({"id": name, "link": meta.get("link"), "order": meta.get("order"), "body": body})
    seen = set()
    for r in rows:
        if r["id"] in seen:
            fails.append(f"REG-002 {r['id']}: duplicate id")
        seen.add(r["id"])
    return rows, fails


def sort_key(r):
    if r["id"].isdigit():
        return (-int(r["id"]), "")
    return (-float(r["order"] or 0), r["id"])


def cell(r):
    return f"[{r['id']}]({r['link']})" if r["link"] else r["id"]


def render(rows):
    return [f"| {cell(r)} | {r['body']} |" for r in sorted(rows, key=sort_key)]


def readme_rows(text):
    a, b = text.find(START), text.find(END)
    if a < 0 or b < 0:
        sys.exit(f"{README}: markers {START} / {END} not found")
    out = {}
    for line in text[a + len(START):b].splitlines():
        m = ROW.match(line)
        if m:
            out[m.group("lid") or m.group("id")] = line
    return out, a, b


def main():
    rows, fails = load()
    text = open(README, encoding="utf-8").read()
    have, a, b = readme_rows(text)
    if "--check" in sys.argv:
        want = {r["id"]: line for r, line in zip(sorted(rows, key=sort_key), render(rows))}
        for rid, line in have.items():
            if rid not in want:
                fails.append(f"REG-003 README row {rid} has no file under docs/adr/register/")
            elif want[rid] != line:
                fails.append(f"REG-003 README row {rid} differs from its file; rerun render_register.py")
        pending = sorted((rid for rid in want if rid not in have), key=lambda i: sort_key({"id": i, "order": next(r["order"] for r in rows if r["id"] == i)}))
        strict = "--strict" in sys.argv
        for f in fails:
            print(f"FAIL [{f}")
        if pending:
            print(("FAIL [REG-003] " if strict else "pending: ") + f"{len(pending)} row(s) not rendered into the README yet: "
                  + ", ".join(pending) + ("" if strict else " (run render_register.py in a refresh PR)"))
        print(f"register: {len(rows)} ruling file(s), {len(have)} README row(s), {len(pending)} pending")
        return 1 if fails or (pending and strict) else 0
    if fails:
        print("\n".join(fails))
        return 1
    new = text[:a + len(START)] + "\n" + "\n".join(render(rows)) + "\n" + text[b:]
    open(README, "w", encoding="utf-8").write(new)
    print(f"rendered {len(rows)} row(s) into {os.path.relpath(README, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

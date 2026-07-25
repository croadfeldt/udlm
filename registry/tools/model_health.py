#!/usr/bin/env python3
"""Model-health scoreboard — registry/MODEL-HEALTH.md + registry/model-health.json.

One per-ref answer to "how healthy is the model?", computed deterministically from the working
tree so every commit carries its own scoreboard. Generated, never hand-edited — regenerate
after any registry/use-case/consumer change:

    python3 registry/tools/model_health.py            # write MD + JSON
    python3 registry/tools/model_health.py --check    # CI: fail if stale
    python3 registry/tools/model_health.py --attest OUT.json
                                                      # CI: emit an attestation artifact —
                                                      # registry ref + scoreboard + gate list —
                                                      # uncommitted (a committed ref would be
                                                      # permanently stale); uploaded by CI and
                                                      # signable downstream (validation results
                                                      # as attestation evidence)

Metrics (all from the tree, no network, no clock):
  - type count by family
  - discrimination density — imports the instance-fuzz harness (fuzz_type_specs.fuzz_type):
    mutations attempted vs rejected per type; a finding is a mutation the spec failed to reject
  - strictness coverage — specs with `additionalProperties: false`; ASSERTED complete (a
    non-strict spec fails this tool, not just the fuzz gate)
  - outputs adequacy — declared-output count per type; 0-output and 1-output types listed
  - context coverage — types carrying a plain-English `context` block
  - relationships coverage — types declaring `relationships[]`
  - UC-family coverage — textual scan of use-cases/*/ YAML for type handles (a dotted handle
    is unambiguous; single-word handles may in principle match prose — noted, accepted)
  - consumer coverage — registry/consumers/ manifests (ADR-044): named-by-consumer vs carried
    only by all-types (envelope-level) consumers
  - named NULL slots for metrics owned by other systems (value null + pending note):
    expressibility_coverage (dav Layer-2), portability_surface (class realization, #199),
    external_corpus_coverage — the scoreboard's shape is complete before those systems report.
"""
import glob
import json
import os
import re
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fuzz_type_specs as fuzz  # noqa: E402  (the instance-fuzz harness; per-type via fuzz_type)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_MD = os.path.join(ROOT, "registry", "MODEL-HEALTH.md")
OUT_JSON = os.path.join(ROOT, "registry", "model-health.json")


def load_types():
    types = {}
    for path in sorted(glob.glob(os.path.join(ROOT, "registry", "resource-types", "*"))):
        if not path.endswith((".json", ".yaml", ".yml")):
            continue
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh) if path.endswith(".json") else yaml.safe_load(fh)
        types[doc["resource_type"]] = (path, doc)
    return types


def discrimination(types):
    per_type, attempted, rejected, findings = {}, 0, 0, 0
    import pathlib
    for rt, (path, _doc) in sorted(types.items()):
        errs, muts = fuzz.fuzz_type(pathlib.Path(path))
        rej = max(muts - len(errs), 0)
        per_type[rt] = {"attempted": muts, "rejected": rej}
        attempted += muts
        rejected += rej
        findings += len(errs)
    return {
        "mutations_attempted": attempted,
        "mutations_rejected": rejected,
        "density": round(rejected / attempted, 4) if attempted else None,
        "findings": findings,
        "per_type": per_type,
    }


def uc_coverage(types):
    texts = []
    for path in sorted(glob.glob(os.path.join(ROOT, "use-cases", "*", "*.yaml"))):
        with open(path, encoding="utf-8") as fh:
            texts.append(fh.read())
    corpus = "\n".join(texts)
    covered, uncovered = [], []
    for rt in sorted(types):
        if re.search(r"\b" + re.escape(rt) + r"\b", corpus):
            covered.append(rt)
        else:
            uncovered.append(rt)
    return {"files_scanned": len(texts), "covered": covered, "uncovered": uncovered}


def consumer_coverage(types):
    named, all_types_consumers = {}, []
    unconsumed_path = os.path.join(ROOT, "registry", "consumers", "unconsumed.yaml")
    for path in sorted(glob.glob(os.path.join(ROOT, "registry", "consumers", "*.yaml"))):
        if os.path.abspath(path) == os.path.abspath(unconsumed_path):
            continue
        with open(path, encoding="utf-8") as fh:
            doc = yaml.safe_load(fh)
        name = doc["consumer"]["name"]
        if doc.get("consumes_all_types") is True:
            all_types_consumers.append(name)
            continue
        for entry in doc.get("consumes") or []:
            named.setdefault(entry["resource_type"], []).append(name)
    named_by_none = sorted(t for t in types if t not in named)
    return {
        "manifests": len(all_types_consumers) + len({c for cs in named.values() for c in cs}),
        "all_types_consumers": sorted(all_types_consumers),
        "named_by_consumer": {t: sorted(cs) for t, cs in sorted(named.items())},
        "named_by_none": named_by_none,
        "consumed_by_at_least_one": len(types) if all_types_consumers else len(named),
    }


def compute():
    types = load_types()
    total = len(types)

    families = {}
    for rt, (_p, d) in types.items():
        families.setdefault(d.get("family", "?"), []).append(rt)
    family_counts = {f: len(ts) for f, ts in sorted(families.items())}

    strict = sorted(rt for rt, (_p, d) in types.items()
                    if (d.get("spec") or {}).get("additionalProperties") is False)
    non_strict = sorted(set(types) - set(strict))
    if non_strict:
        # Strictness is a settled invariant (strict-by-default ruling; the fuzz gate enforces
        # it per-mutation) — a non-strict spec is a red state here too, not a statistic.
        print(f"FAIL: {len(non_strict)} spec(s) without additionalProperties: false: "
              f"{', '.join(non_strict)}")
        sys.exit(1)

    output_counts = {rt: len(d.get("outputs") or {}) for rt, (_p, d) in sorted(types.items())}
    zero_out = sorted(rt for rt, n in output_counts.items() if n == 0)
    one_out = sorted(rt for rt, n in output_counts.items() if n == 1)

    with_context = sorted(rt for rt, (_p, d) in types.items() if d.get("context"))
    with_rels = sorted(rt for rt, (_p, d) in types.items() if d.get("relationships"))

    return {
        "scoreboard": "udlm-model-health/1",
        "totals": {"types": total, "by_family": family_counts},
        "discrimination": discrimination(types),
        "strictness": {"strict_specs": len(strict), "total": total},
        "outputs": {
            "per_type": output_counts,
            "zero_output_types": zero_out,
            "one_output_types": one_out,
        },
        "context": {"with_context": len(with_context), "total": total,
                    "missing": sorted(set(types) - set(with_context))},
        "relationships": {"with_relationships": len(with_rels), "total": total,
                          "missing": sorted(set(types) - set(with_rels))},
        "uc_coverage": uc_coverage(types),
        "consumer_coverage": consumer_coverage(types),
        "expressibility_coverage": {"value": None, "note": "pending — dav Layer-2 (data-model-validation design) reports this"},
        "portability_surface": {"value": None, "note": "pending — Class realization (#199) makes this measurable"},
        "external_corpus_coverage": {"value": None, "note": "pending — no external UC corpus wired yet"},
    }


def pct(n, d):
    return f"{n}/{d} ({100 * n // d}%)" if d else "n/a"


def render_md(h):
    t = h["totals"]["types"]
    disc = h["discrimination"]
    uc = h["uc_coverage"]
    cc = h["consumer_coverage"]
    fam = ", ".join(f"{k} {v}" for k, v in h["totals"]["by_family"].items())

    lines = [
        "# Model health — the registry's per-ref scoreboard",
        "",
        "> GENERATED by `registry/tools/model_health.py` from the working tree — edit the model,",
        "> regenerate, never edit here. `--check` gates staleness in CI. Numbers pair with",
        "> `registry/model-health.json` (the machine-readable projection of this file).",
        "",
        f"The registry holds **{t} types** ({fam}). Every spec is strict"
        f" (`additionalProperties: false`, {pct(h['strictness']['strict_specs'], t)}) and the"
        f" instance-fuzz harness rejected {disc['mutations_rejected']} of"
        f" {disc['mutations_attempted']} adversarial mutations"
        f" ({disc['density']:.2%} discrimination density, {disc['findings']} open finding(s))."
        f" {pct(len(uc['covered']), t)} of types appear in at least one use case;"
        f" {len(uc['uncovered'])} appear in none."
        f" {len(cc['named_by_consumer'])} types are named by a specific consumer manifest;"
        f" the other {len(cc['named_by_none'])} are carried only by the"
        f" {len(cc['all_types_consumers'])} envelope-level (all-types) consumers."
        f" {len(h['outputs']['zero_output_types'])} types declare no outputs and"
        f" {len(h['outputs']['one_output_types'])} declare exactly one — the thinnest part of"
        " the binding surface. Three metrics are owned by other systems and report null until"
        " those systems land (table at the end).",
        "",
        "## Headline",
        "",
        "| Metric | Value | Reading |",
        "|---|---|---|",
        f"| Types (by family) | {t} ({fam}) | — |",
        f"| Discrimination density | {disc['mutations_rejected']}/{disc['mutations_attempted']}"
        f" = {disc['density']:.2%} | mutations rejected / attempted; {disc['findings']} finding(s) |",
        f"| Strictness coverage | {pct(h['strictness']['strict_specs'], t)} | asserted — a non-strict spec fails this tool |",
        f"| Outputs adequacy | {len(h['outputs']['zero_output_types'])} zero-output, "
        f"{len(h['outputs']['one_output_types'])} one-output | declared Realized binding surface |",
        f"| Context coverage | {pct(h['context']['with_context'], t)} | plain-English `context` blocks |",
        f"| Relationships coverage | {pct(h['relationships']['with_relationships'], t)} | types declaring `relationships[]` |",
        f"| UC coverage | {pct(len(uc['covered']), t)} | types appearing in >=1 use case ({uc['files_scanned']} UC files scanned) |",
        f"| Consumer coverage | {pct(cc['consumed_by_at_least_one'], t)} | ADR-044 manifests; "
        f"{len(cc['named_by_consumer'])} named explicitly, rest via all-types consumers |",
        "",
        "## Outputs adequacy",
        "",
        "Outputs are the contract-checked binding surface — a type with none publishes nothing a",
        "downstream consumer can bind on.",
        "",
        f"**Zero-output types ({len(h['outputs']['zero_output_types'])}):** "
        + (", ".join(f"`{x}`" for x in h["outputs"]["zero_output_types"]) or "none"),
        "",
        f"**One-output types ({len(h['outputs']['one_output_types'])}):** "
        + (", ".join(f"`{x}`" for x in h["outputs"]["one_output_types"]) or "none"),
        "",
        "## UC coverage gaps",
        "",
        f"Types appearing in no use case ({len(uc['uncovered'])}) — each is either ahead of its",
        "scenarios or untested by any story (textual scan; a dotted handle is unambiguous,",
        "single-word handles could in principle match prose):",
        "",
    ]
    lines += [f"- `{x}`" for x in uc["uncovered"]] or ["- none"]
    lines += [
        "",
        "## Consumer coverage",
        "",
        f"All-types (envelope-level) consumers: "
        + (", ".join(f"`{x}`" for x in cc["all_types_consumers"]) or "none")
        + ". Types named by a specific manifest:",
        "",
        "| Type | Named by |",
        "|---|---|",
    ]
    lines += [f"| `{rt}` | {', '.join(cs)} |" for rt, cs in cc["named_by_consumer"].items()]
    lines += [
        "",
        "## Coverage detail",
        "",
        f"- Context blocks missing ({len(h['context']['missing'])}): "
        + (", ".join(f"`{x}`" for x in h["context"]["missing"]) or "none"),
        f"- `relationships[]` missing ({len(h['relationships']['missing'])}): "
        + (", ".join(f"`{x}`" for x in h["relationships"]["missing"]) or "none"),
        "",
        "## Pending metrics (owned elsewhere, shape reserved)",
        "",
        "| Metric | Value | Owner |",
        "|---|---|---|",
        f"| expressibility_coverage | null | {h['expressibility_coverage']['note']} |",
        f"| portability_surface | null | {h['portability_surface']['note']} |",
        f"| external_corpus_coverage | null | {h['external_corpus_coverage']['note']} |",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    health = compute()
    md = render_md(health)
    js = json.dumps(health, indent=2) + "\n"
    if "--attest" in sys.argv:
        import subprocess
        out_path = sys.argv[sys.argv.index("--attest") + 1]
        ref = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                             text=True, cwd=str(ROOT)).stdout.strip()
        attestation = {
            "attestation_subject": "model-validation",
            "registry_ref": ref,
            "scoreboard": health,
            "gate_suite": "registry validate.yml (deterministic hammers: fuzz, composition, "
                          "provider cross-check, consumer conformance, scoreboard currency)",
            "note": "Emitted by CI after the gate suite passed on registry_ref; a failed suite "
                    "emits nothing. Signing/anchoring is the attestation pipeline's act.",
        }
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(attestation, indent=2) + "\n")
        print(f"wrote attestation artifact {out_path} for {ref}")
        return 0
    if "--check" in sys.argv:
        cur_md = open(OUT_MD, encoding="utf-8").read() if os.path.exists(OUT_MD) else ""
        cur_js = open(OUT_JSON, encoding="utf-8").read() if os.path.exists(OUT_JSON) else ""
        if cur_md != md or cur_js != js:
            print("STALE: registry/MODEL-HEALTH.md / model-health.json do not match the tree — regenerate.")
            return 1
        print("MODEL-HEALTH.md and model-health.json are current.")
        return 0
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(md)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        fh.write(js)
    print(f"wrote {OUT_MD}\nwrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

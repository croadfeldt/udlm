#!/usr/bin/env python3
"""Valid-by-construction gate. Validates:
  - registry/generated/*       against  resource-type-spec.schema.json        (served TYPE projections)
  - registry/profiles/*        against  profile.schema.json                   (deployment PROFILES)
  - registry/taxonomies/*      against  the taxonomy-seed shape               (governed VOCABULARY seeds)
  - registry/examples/*        against  realized-entity.schema.json           (worked EXAMPLE records)
                        or against  policy / layer / catalog-item / audit / accreditation schemas
                        or against  profile.schema.json                       (PROFILE records — activatable postures)
                        or against  catalog-item.schema.json                  (Composite Service catalog items)
Instance dispatch: `record_type` is the dispatch key going forward (catalog_item → catalog
schema); legacy discriminators remain — a document with `record_type: profile` is a profile;
grouping; one with `resource_type` is a realized entity (data-model-core §5 — Tenants ARE
groupings). Catalog items additionally get semantic checks JSON Schema cannot express
(component_id uniqueness, sibling depends_on/binding resolution, cycle rejection,
binding⊆depends_on ordering).
Loads JSON and YAML natively. Exit non-zero if anything is invalid. Wire into CI."""
import glob
import json
import re
import sys
import pathlib

# refstore lives beside this file, so it must be importable when validate.py is imported BY a gate
# in tests/ rather than run from here — otherwise the failure surfaces as the misleading
# "requires: pip install jsonschema" below, which is what happened the first time.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import refstore as _refstore  # noqa: E402  (path must be set first)

try:
    from jsonschema import Draft202012Validator, RefResolver
except ImportError:
    sys.exit("requires: pip install jsonschema")
try:
    import yaml
except ImportError:
    yaml = None

ROOT = pathlib.Path(__file__).resolve().parent.parent
def _ref_store():
    """Shared with the fuzz, spec-example and generator gates (registry/tools/refstore.py).

    This used to be a hardcoded list of four schemas. It resolved everything those four needed and
    nothing else, so a $ref to a fifth — the mechanism SPEC-DESIGN §33 prescribes for a shared
    vocabulary — raised Unresolvable here while passing under the gates that globbed."""
    return _refstore.build_store()

def _validator(name):
    """A validator whose $refs resolve against the shared offline store.

    Every one of these was built bare — `Draft202012Validator(json.loads(...))` with no resolver —
    which works only for as long as no schema $refs another. The moment one did (the shared
    vocabularies in common-elements.schema.json), fourteen validators would have had to be fixed
    one at a time, and the failure mode is a DNS lookup rather than a clear error. Built through one
    helper so a shared $ref works everywhere or nowhere."""
    doc = json.loads((ROOT / name).read_text())
    return Draft202012Validator(doc, resolver=RefResolver(base_uri=(ROOT / name).as_uri(),
                                                          referrer=doc, store=_ref_store()))


TYPE_VALIDATOR = _validator("resource-type-spec.schema.json")
INSTANCE_VALIDATOR = _validator("realized-entity.schema.json")
PROFILE_VALIDATOR = _validator("profile.schema.json")
_CATALOG_SCHEMA = json.loads((ROOT / "catalog-item.schema.json").read_text())
CATALOG_VALIDATOR = None   # bound below, once _ref_store() is defined
CONFORMANCE_DECL_VALIDATOR = _validator("conformance-declaration.schema.json")
POLICY_VALIDATOR = _validator("policy.schema.json")
EVAL_CONTEXT_VALIDATOR = _validator("evaluation-context.schema.json")
LAYER_VALIDATOR = _validator("layer.schema.json")
VOCABULARY_TERM_VALIDATOR = _validator("vocabulary-term.schema.json")
REGISTRATION_VERDICT_VALIDATOR = _validator("registration-verdict.schema.json")
PROMOTION_EVIDENCE_VALIDATOR = _validator("promotion-evidence.schema.json")
LOG_CHECKPOINT_VALIDATOR = _validator("log-checkpoint.schema.json")
AUDIT_RECORD_VALIDATOR = _validator("audit-record.schema.json")
COMMIT_LOG_VALIDATOR = _validator("commit-log-entry.schema.json")
AUDIT_LEAF_VALIDATOR = _validator("audit-leaf.schema.json")
DECISION_VALIDATOR = _validator("decision-record.schema.json")
REGENERATION_VALIDATOR = _validator("regeneration-manifest.schema.json")
FINDING_ROUTING_VALIDATOR = _validator("finding-routing-record.schema.json")
ACCREDITATION_VALIDATOR = _validator("accreditation.schema.json")
_COMPOSITION_RECORD_SCHEMA = json.loads((ROOT / "composition-record.schema.json").read_text())
COMPOSITION_RECORD_VALIDATOR = None   # bound below, once _ref_store() is defined
_CLASS_SCHEMA = json.loads((ROOT / "class.schema.json").read_text())

_CLASS_RESOLVER = RefResolver(base_uri=(ROOT / "class.schema.json").as_uri(), referrer=_CLASS_SCHEMA,
                              store=_ref_store())
CLASS_VALIDATOR = Draft202012Validator(_CLASS_SCHEMA, resolver=_CLASS_RESOLVER)
# catalog-item $refs the shared composition shape (composition.schema.json), so it resolves the
# same way a class does rather than as a self-contained document.
CATALOG_VALIDATOR = Draft202012Validator(
    _CATALOG_SCHEMA,
    resolver=RefResolver(base_uri=(ROOT / "catalog-item.schema.json").as_uri(),
                         referrer=_CATALOG_SCHEMA, store=_ref_store()))
# A composition record $refs the same shared composition shape a class does — one shape, so
# promotion is not a translation. Resolved the same way for the same reason.
COMPOSITION_RECORD_VALIDATOR = Draft202012Validator(
    _COMPOSITION_RECORD_SCHEMA,
    resolver=RefResolver(base_uri=(ROOT / "composition-record.schema.json").as_uri(),
                         referrer=_COMPOSITION_RECORD_SCHEMA, store=_ref_store()))
TAXONOMY_SEED_VALIDATOR = Draft202012Validator({"type": "object", "required": ["terms"], "properties": {"terms": {"type": "array"}}})


def _type_outputs_index():
    """resource_type -> set(declared output names). The typed-outputs surface a catalog-item
    binding resolves against (data-model-core §2 [D8.3])."""
    index = {}
    for base in (ROOT / "resource-types", ROOT / "generated"):
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.suffix not in (".json", ".yaml", ".yml"):
                continue
            doc = load(path)
            if isinstance(doc, dict) and doc.get("resource_type"):
                index[doc["resource_type"]] = set((doc.get("outputs") or {}).keys())
    return index


def load(path: pathlib.Path):
    text = path.read_text()
    if path.suffix in (".yaml", ".yml"):
        if yaml is None:
            sys.exit(f"pyyaml required to load {path.name}")
        return yaml.safe_load(text)
    return json.loads(text)


def load_all(path: pathlib.Path):
    """Load one file into a LIST of records. A .yaml/.yml file MAY be a multi-document stream
    (`---`-separated) — each document is a self-describing record (its own `record_type`) and is
    validated independently, the k8s multi-object-in-one-file idiom (a base data-layer + its
    overlays; a provider + its own accreditations). JSON is single-document. Empty documents
    (trailing `---`, comment-only) are dropped so they don't dispatch as null."""
    text = path.read_text()
    if path.suffix in (".yaml", ".yml"):
        if yaml is None:
            sys.exit(f"pyyaml required to load {path.name}")
        return [d for d in yaml.safe_load_all(text) if d is not None]
    return [json.loads(text)]


def validate_dir(subdir: str, pick) -> int:
    """pick(doc) -> (validator, label_fn[, checks_fn]) — per-document dispatch.
    checks_fn(doc) -> [error strings] runs semantic checks JSON Schema cannot express;
    any returned error makes the document invalid."""
    failures = 0
    base = ROOT / subdir
    if not base.exists():
        return 0
    for path in sorted(base.rglob("*")):
        # must-reject cases are INPUTS to a gate, not documents to validate — the ordinary validator
        # would report the very errors they exist to provoke. tests/check_must_reject.py executes
        # them, and fails if any is ACCEPTED.
        if "must-reject" in path.parts:
            continue
        if path.suffix not in (".json", ".yaml", ".yml"):
            continue
        docs = load_all(path)
        multi = len(docs) > 1
        for i, doc in enumerate(docs):
            tag = f"{path.name}#{i}" if multi else path.name   # k8s-style: one record per doc in a `---` stream
            picked = pick(doc)
            validator, label = picked[0], picked[1]
            checks = picked[2] if len(picked) > 2 else None
            errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.path))
            semantic = checks(doc) if checks and not errors else []
            if errors or semantic:
                failures += 1
                print(f"FAIL {tag}")
                for err in errors[:5]:
                    loc = "/".join(str(p) for p in err.path) or "(root)"
                    print(f"   - {loc}: {err.message}")
                for msg in semantic:
                    print(f"   - {msg}")
            else:
                print(f"ok   {tag}  — {label(doc)}")
    return failures


def check_class_constituents(doc):
    """Composite-definition semantic checks for a Class carrying `constituents` — the SAME
    cross-field constraints as a composite catalog item (one shape, one checker: reuse
    check_catalog_item), plus namespace resolution: each constituent's resource_type must
    resolve to a registered Class or a flat resource type (both legal during the migration —
    the one dotted namespace)."""
    if not doc.get("constituents"):
        return []
    errors = check_catalog_item(doc) + check_constituent_edges(doc)
    known = _known_type_names()
    for c in doc.get("constituents", []):
        rt = c.get("resource_type")
        if rt and rt not in known:
            errors.append(f"CMP-011 constituent '{c.get('component_id','?')}': resource_type {rt!r} "
                          f"resolves to neither a registered Class nor a flat resource type")
    return errors


def check_constituent_edges(doc):
    """CMP-012 — a constituent the composite does not create cannot be one it owns.

    `edge_type` says whether the composite OWNS a part (`contained_by`) or merely uses one
    (`binds_to`). `fulfillment: consumer` says the consumer supplies an EXISTING resource — BYO. A
    thing you were handed a reference to is not a thing you created, so it cannot be a part; it is a
    stake in someone else's resource.

    The distinction is not stylistic. GRP-INV-002 is non-overridable: the parts of one thing may not
    span two owners. Modelled as `contained_by`, a BYO resource makes the composite claim ownership
    of something another tenant holds — and at realization that is either a refusal or, worse, a
    silent ownership transfer of a resource other tenants are also using.

    What cannot be checked here: whether a `contained_by` constituent's target is actually co-tenant.
    At catalog time a constituent names a TYPE, not an instance, so there is no owner to compare —
    that check belongs at realization, where check_group_invariants already makes it.
    """
    errors = []
    for c in doc.get("constituents") or []:
        if c.get("edge_type", "contained_by") == "contained_by" and c.get("fulfillment") == "consumer":
            errors.append(f"CMP-012 constituent '{c.get('component_id','?')}': fulfillment 'consumer' "
                          f"means the consumer supplies an EXISTING resource, which the composite "
                          f"cannot also own — declare edge_type 'binds_to' (a stake), not "
                          f"'contained_by' (a part)")
    return errors


def check_ownership_declaration(doc):
    """OWN-007 / OWN-008 made enforceable — the ownership declaration must be internally coherent
    and its pool linkage must round-trip.

    OWN-007 ("the ownership model for a resource type is declared in the Resource Type
    Specification … a type-level invariant") and OWN-008 ("… or the resource type is declared as
    publicly allocatable/stakeable in its Resource Type Spec") have been normative since 0.1 and
    unenforceable the whole time: neither `ownership_model` nor `publicly_stakeable` existed in any
    schema, so the rules named fields nothing could carry. These checks are the other half.

    Applies identically to a Class (the authoring tier) and a compiled flat spec — same field names,
    one checker.
    """
    om = doc.get("ownership_model")
    pool_of = doc.get("allocated_from_pool_type")
    produces = doc.get("allocation_produces_type")
    errors = []

    # an allocation is carved from a pool: the linkage is required, and meaningless without it
    if om == "allocation" and not pool_of:
        errors.append("OWN-007: ownership_model 'allocation' requires allocated_from_pool_type — "
                      "an allocation with no pool to be carved from is not an allocation")
    if pool_of and om != "allocation":
        errors.append(f"OWN-007: allocated_from_pool_type is set but ownership_model is {om!r}; "
                      f"it is meaningful only for 'allocation'")

    # OWN-008's standing declarations are per-pattern: a stake is a stake, an allocation is carved
    if doc.get("publicly_stakeable") and om != "shareable":
        errors.append(f"OWN-008: publicly_stakeable requires ownership_model 'shareable' (got {om!r}) "
                      f"— only a shareable resource is staked")
    if doc.get("publicly_allocatable") and not produces:
        errors.append("OWN-008: publicly_allocatable is meaningful only on a POOL — a type declaring "
                      "allocation_produces_type")

    # the pool <-> allocation pair must agree, or placement resolves to a type that disowns it
    if produces:
        idx = _ownership_index()
        target = idx.get(produces)
        if target is None:
            errors.append(f"OWN-002: allocation_produces_type {produces!r} resolves to no known type")
        else:
            if target.get("ownership_model") != "allocation":
                errors.append(f"OWN-002: this type is a pool producing {produces!r}, but that type "
                              f"declares ownership_model {target.get('ownership_model')!r}, not 'allocation'")
            back = target.get("allocated_from_pool_type")
            if back != doc.get("resource_type"):
                errors.append(f"OWN-002: pool linkage does not round-trip — {produces!r} is carved from "
                              f"{back!r}, not from {doc.get('resource_type')!r}")
    return errors


_OWNERSHIP_INDEX = None
def _ownership_index():
    """resource_type -> its ownership declaration. Cached; built once because the round-trip check is
    cross-record and every record asks the same question.

    Sources are the AUTHORING tier only — classes/ plus the not-yet-migrated flat specs in
    resource-types/ — deliberately NOT generated/. A compiled spec is a projection of its class and
    contributes nothing the class does not already say, but indexing it lets a STALE artifact mask a
    broken class: a first cut of this check indexed generated/ last, so breaking the pool linkage in
    Network.IPAddress's class produced no failure because the stale compiled copy still round-tripped.
    Staleness is GEN-001's job; this check must not depend on that gate having run first."""
    global _OWNERSHIP_INDEX
    if _OWNERSHIP_INDEX is None:
        idx = {}
        pats = [str(ROOT / "classes" / "**" / "*.yaml"),
                str(ROOT / "resource-types" / "**" / "*.json")]
        for pat in pats:
            for path in glob.glob(pat, recursive=True):
                try:
                    d = (yaml.safe_load(open(path, encoding="utf-8")) if path.endswith(".yaml")
                         else json.loads(open(path, encoding="utf-8").read())) or {}
                except Exception:
                    continue
                rt = d.get("resource_type")
                if not isinstance(d, dict) or not rt:
                    continue
                # nearest-wins is not a concern: a type is declared once, and the class and its
                # compiled spec agree by construction (the generator copies the block verbatim)
                idx.setdefault(rt, {}).update(
                    {k: d[k] for k in ("ownership_model", "allocated_from_pool_type",
                                       "allocation_produces_type") if k in d})
        _OWNERSHIP_INDEX = idx
    return _OWNERSHIP_INDEX


def check_class_record(doc):
    """Every semantic check a Class record gets: the composite definition and the ownership
    declaration. Split into two functions because a flat spec gets the second and not the first."""
    return check_class_constituents(doc) + check_ownership_declaration(doc)


_KNOWN_TYPES = None
def _known_type_names():
    """Class names (registry/classes) + flat resource types (registry/resource-types) — cached."""
    global _KNOWN_TYPES
    if _KNOWN_TYPES is None:
        names = set()
        for path in glob.glob(str(ROOT / "classes" / "**" / "*.yaml"), recursive=True):
            d = yaml.safe_load(open(path, encoding="utf-8")) or {}
            if d.get("record_type") == "class":
                names.add(d.get("resource_type"))
        for path in glob.glob(str(ROOT / "resource-types" / "**" / "*"), recursive=True):
            if path.endswith((".json", ".yaml", ".yml")):
                try:
                    d = (yaml.safe_load(open(path, encoding="utf-8")) if path.endswith((".yaml", ".yml"))
                         else json.loads(open(path, encoding="utf-8").read())) or {}
                except Exception:
                    continue
                if d.get("resource_type"):
                    names.add(d["resource_type"])
        _KNOWN_TYPES = names
    return _KNOWN_TYPES


def check_catalog_item(doc):
    """Semantic checks for Composite Service catalog items — the cross-field constraints
    JSON Schema cannot express (catalog-item.schema.json description; composite-service-model.md
    §2.3/§10 registration rejection rules):
      (a) component_id unique within the item
      (b) every depends_on / bindings.from_component resolves to a sibling component_id
      (c) the depends_on graph is acyclic (CMP-002 ordering derives from it)
      (d) a binding's from_component appears in that constituent's depends_on
          (data movement implies ordering)."""
    errors = []
    constituents = doc.get("constituents", [])

    # (a) component_id uniqueness
    ids = [c.get("component_id") for c in constituents]
    seen = set()
    for cid in ids:
        if cid in seen:
            errors.append(f"constituents: duplicate component_id '{cid}' — must be unique within the item")
        seen.add(cid)
    id_set = set(ids)

    # (b) sibling resolution + (d) binding ⊆ depends_on
    for c in constituents:
        cid = c.get("component_id", "?")
        deps = c.get("depends_on", [])
        for dep in deps:
            if dep not in id_set:
                errors.append(f"CMP-010 constituent '{cid}': depends_on '{dep}' does not resolve to a "
                             f"sibling component_id")
        for b in c.get("bindings", []):
            src = b.get("from_component")
            if src not in id_set:
                errors.append(f"constituent '{cid}': binding from_component '{src}' does not resolve to a sibling component_id")
            elif src not in deps:
                errors.append(f"constituent '{cid}': binding from_component '{src}' missing from depends_on — data movement implies ordering")

    # (c) cycle detection — DFS, 3-color
    graph = {c.get("component_id"): [d for d in c.get("depends_on", []) if d in id_set]
             for c in constituents}
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {cid: WHITE for cid in graph}

    def dfs(node, path):
        color[node] = GRAY
        for dep in graph.get(node, []):
            if color[dep] == GRAY:
                cycle = path[path.index(dep):] + [dep] if dep in path else [node, dep]
                errors.append("CMP-002 constituents: depends_on cycle " + " -> ".join(cycle))
                return True
            if color[dep] == WHITE and dfs(dep, path + [dep]):
                return True
        color[node] = BLACK
        return False

    for cid in graph:
        if color[cid] == WHITE and dfs(cid, [cid]):
            break  # one reported cycle is enough

    # (e) binding output type-safety: a binding's `output` must be a DECLARED output of the
    #     producer constituent's resource_type (data-model-core §2 [D8.3] typed outputs).
    #     Skip gracefully if the type is not in the registry; FAIL if the type is known and the
    #     output is not one of its declared output names.
    type_outputs = _type_outputs_index()
    rt_of = {c.get("component_id"): c.get("resource_type") for c in constituents}
    for c in constituents:
        cid = c.get("component_id", "?")
        for b in c.get("bindings", []):
            src, out = b.get("from_component"), b.get("output")
            src_type = rt_of.get(src)
            if src_type in type_outputs and out not in type_outputs[src_type]:
                declared = sorted(type_outputs[src_type]) or ["(none declared)"]
                errors.append(
                    f"constituent '{cid}': binding output '{src}.{out}' is not a declared output of "
                    f"{src_type} (declared: {', '.join(declared)})")

    return errors



def _type_family_index():
    """resource_type -> family (Resource | Process | Knowledge | Access — ADR-027)."""
    index = {}
    for path in (ROOT / "resource-types").rglob("*"):
        if path.suffix not in (".json", ".yaml", ".yml"):
            continue
        doc = load(path)
        index[doc["resource_type"]] = doc.get("family")
    return index


def check_process_entity(doc):
    """A realized entity whose Resource Type is family: Process MUST carry the `process`
    execution axis with an execution_state (resource-service-entities §6.3; data-model-core §3
    [D7]). Non-Process entities must NOT carry it.

    Keys on `family`, not `entity_type` — ADR-027 moved the state-vs-execution distinction to
    the family tier; `entity_type` is now the Atomic/Composite shape (a Process is
    family: Process, entity_type: Atomic|Composite). The prior `entity_type == "Process"` test
    was dead — it never matched, and false-failed the correct example instance (now example-job) instance."""
    errors = []
    rt = doc.get("resource_type")
    fam = _type_family_index().get(rt)
    has_proc = isinstance(doc.get("process"), dict)
    if fam == "Process" and not has_proc:
        errors.append(f"{rt} is family: Process but the instance has no `process` block "
                      f"(execution_state required; §6.3 / D7)")
    if fam and fam != "Process" and has_proc:
        errors.append(f"{rt} is family: {fam}, not Process — it must not carry a `process` "
                      f"execution axis")
    return errors


def check_taxonomy_seed(doc):
    """A taxonomy seed (registry/examples/*-taxonomy.yaml, term_type: TaxonomyTerm) is a batch of
    governed vocabulary terms, not a realized entity. Each term MUST carry `term` + `definition`;
    every non-root `parent` MUST resolve to a term in the file (dangling-parent check)."""
    errors = []
    terms = doc.get("terms") or []
    handles = {t.get("term") for t in terms}
    for t in terms:
        if not t.get("term") or not t.get("definition"):
            errors.append(f"taxonomy term '{t.get('term', '?')}' missing term/definition")
        p = t.get("parent")
        if p and p not in handles:
            errors.append(f"taxonomy term '{t.get('term', '?')}' has dangling parent '{p}'")
    return errors


def _spec_field_paths(schema, prefix=""):
    """Dot-paths of every field declared in a type-spec `spec` (recursing into object props)."""
    out = set()
    for name, sub in ((schema or {}).get("properties") or {}).items():
        p = f"{prefix}{name}"
        out.add(p)
        if isinstance(sub, dict) and sub.get("type") == "object":
            out |= _spec_field_paths(sub, p + ".")
    return out


_UUID_V4_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


def check_provider_extensions(doc):
    """provider_extensions is RETIRED (removed 2026-07-23, executing #202): provider-specific
    data is a Provider-Class `SharedDataElement` (ADR-038; schema realization #199). Any
    instance still carrying the field is rejected so the retirement cannot silently regress.
    The enduring obligations (additive-only, portability degradation, consumer notification)
    live on the `portability` block and the Transparency principle."""
    if "provider_extensions" in doc:
        return ["carries the retired `provider_extensions` field — provider-specific data is a "
                "Provider-Class SharedDataElement (ADR-038; schema realization #199); re-home "
                "the values and record portability on the `portability` block"]
    return []


def _reference_data_index():
    """uuid -> the governed term it identifies, for {ref_uuid,ref_name} integrity (ADR-012).

    Reads BOTH homes while the retirement is in flight: `record_type: vocabulary_term` (the home
    ADR-058 settled) and the legacy `record_type: layer` + `layer_type: reference_data`. Reading
    both is deliberate — a reference must not break in the window between the vocabulary half of
    the migration and the context/taxonomy halves, and a resolver that silently stopped finding a
    referent would turn a structural move into a corpus of dangling edges."""
    index = {}
    for base in (ROOT / "examples", ROOT / "profiles", ROOT / "taxonomies"):
        if not base.exists():
            continue
        for path in base.glob("*"):
            if path.suffix not in (".json", ".yaml", ".yml"):
                continue
            for doc in load_all(path):                       # multi-doc aware (`---` streams)
                if not isinstance(doc, dict):
                    continue
                is_term = doc.get("record_type") == "vocabulary_term"
                is_legacy = (doc.get("record_type") == "layer"
                             and doc.get("layer_type") == "reference_data")
                if is_term or is_legacy:
                    index[doc.get("uuid")] = {
                        # One key either way: a consumer's `?reference_data_type==<kind>` predicate
                        # resolves against the same field name whichever home answered it.
                        "reference_data_type": (doc.get("vocabulary_kind") if is_term
                                                else doc.get("reference_data_type")),
                        "handle": doc.get("handle"),
                        "name": doc.get("name"),
                        "version": doc.get("version"),
                        "state": (doc.get("status") or {}).get("state"),
                        "supersedes": doc.get("supersedes") or [],
                    }
    return index


def _ver_tuple(v):
    """Parse a MAJOR.MINOR.REVISION string into a comparable tuple; unparseable -> (0,0,0)."""
    try:
        return tuple(int(p) for p in str(v).split("."))
    except (ValueError, AttributeError):
        return (0, 0, 0)


def _successor_index(index):
    """Forward lineage: uuid -> [uuids that DIRECTLY supersede it], derived from the explicit
    `supersedes` DAG (ADR-012 — the single lineage mechanism; `handle` is not consulted)."""
    succ = {}
    for uuid, e in index.items():
        for prior in e.get("supersedes") or []:
            succ.setdefault(prior, []).append(uuid)
    return succ


def _descendants(uuid, succ):
    """All uuids that supersede `uuid` transitively (its newer versions), walking the successor DAG."""
    out, frontier = set(), list(succ.get(uuid, []))
    while frontier:
        u = frontier.pop()
        if u in out:
            continue
        out.add(u)
        frontier.extend(succ.get(u, []))
    return out


def _find_data_references(obj, path=""):
    """Yield (dot-path, target_uuid) for every data reference embedded in a record.

    A reference is a URF STRING — `uuid/<v4>[@version][?reference_data_type==<kind>]`
    (ADR-012 + identifier-scheme §9).

    THIS READ THE WRONG SHAPE FOR MONTHS. It looked for a dict carrying `ref_uuid` — the k8s
    ObjectReference form the corpus left behind at the URF cutover (the superseding records say so
    by name: "the object-form example this replaces"). `check_data_references` was moved to URF
    strings; this was not, and it is the ONLY input to the change-impact graph. So `impact_report`
    found no edges and printed "0 reference(s) pinned to a superseded version" on every run — while
    the corpus deliberately staged the case it exists to show: app_profile pins network_zone v1,
    v2 supersedes v1. A clean-looking zero, over a graph with no edges in it.

    Kept as one helper so the two can never disagree again: whatever `check_data_references`
    validates is what the impact graph traverses."""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out += _find_data_references(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out += _find_data_references(v, f"{path}[{i}]")
    elif isinstance(obj, str) and obj.startswith("uuid/") and "reference_data_type==" in obj:
        parts = obj[len("uuid/"):].split("?")[0].split("@")[0].split("/")
        if parts and parts[0]:
            out.append((path or "(root)", parts[0]))
    return out


def check_schedule_clauses(doc):
    """Temporal clauses govern WHEN, never WHETHER (ADR-053).

    The clause object is closed and carries no decision field, so "cannot encode a decision" is
    structural. Three things the schema still cannot say:

    - `expedite` requires an approval at an ELEVATED authority. Without that, compressing the
      calendar needs no more standing than following it, and the exception becomes the cheap path.
    - `schedule` belongs on a `validation` or `orchestration_flow` policy — the two that decide
      whether a change proceeds. Elsewhere it reads as though timing could decide a question the
      policy does not itself answer.
    - a `precondition` must name the stage it waits on. One that names nothing waits on nothing and
      passes silently, which is worse than not declaring it."""
    sched = doc.get("schedule")
    if not isinstance(sched, list):
        return []
    errors = []
    pt = doc.get("policy_type")
    if pt not in ("validation", "orchestration_flow"):
        errors.append(f"schedule: a temporal clause on a {pt!r} policy — schedule governs WHEN a "
                      f"change may run, so it belongs on `validation` or `orchestration_flow`. "
                      f"Elsewhere it reads as though timing could decide a question the policy does "
                      f"not itself answer")
    for i, c in enumerate(sched):
        kind = c.get("kind")
        if kind == "expedite":
            ap = c.get("approval") or {}
            if not ap:
                errors.append(f"schedule[{i}] expedite: no approval. Compressing the calendar under "
                              f"no sign-off makes the exception cheaper than the rule")
            elif not ap.get("authority_level"):
                errors.append(f"schedule[{i}] expedite: the approval names no `authority_level`. "
                              f"Expedite requires an ELEVATED authority the policy declares — "
                              f"otherwise it needs no more standing than following the calendar")
        if kind == "precondition" and not c.get("predecessor_stage"):
            errors.append(f"schedule[{i}] precondition: names no `predecessor_stage`. A "
                          f"precondition that waits on nothing passes silently, which is worse "
                          f"than not declaring one")
        if kind == "freeze" and not (c.get("effective_from") or c.get("effective_until")):
            errors.append(f"schedule[{i}] freeze: undated. A freeze QUEUES rather than runs, so an "
                          f"undated one queues forever and the change is lost rather than deferred")
    return errors


def check_provider_preference(doc):
    """A pin decides WHICH eligible provider, never WHETHER an ineligible one is reached (ADR-050).

    JSON Schema closes the object, so no bypass field can be added. What it cannot check is the
    sentence around it: a record that pairs a preference with language claiming the ceiling is
    waived has written the exception the decision exists to prevent. Cheap to catch, and the whole
    value of the rule is that it holds on every path — one exception makes the invariant
    unstatable."""
    pref = doc.get("provider_preference")
    if not isinstance(pref, dict):
        return []
    errors = []
    blob = " ".join(str(v) for v in pref.values()).lower()
    for phrase in ("bypass", "override the ceiling", "ignore capability", "force dispatch",
                   "regardless of capability", "waive"):
        if phrase in blob:
            errors.append(
                f"provider_preference: {phrase!r} — a pin is preference among ELIGIBLE providers. "
                f"The effective_capabilities ceiling applies at the dispatch boundary on every path "
                f"(PRV-009/PRV-011); a pin naming an ineligible provider is refused with "
                f"placement.capability_mismatch before dispatch. A deliberate bypass is policy's "
                f"call (ADR-008), never a field here")
    return errors


def check_log_checkpoint(doc):
    """A checkpoint must extend what it supersedes, and every signature must be over one statement.

    Schema can require the fields. It cannot check that a checkpoint claiming to supersede an
    earlier one actually covers MORE of the log — and a checkpoint that supersedes a larger tree is
    the artifact a rewrite produces, so it is the one thing worth refusing structurally."""
    errors = []
    if doc.get("tree_size") == 0 and doc.get("supersedes"):
        errors.append("tree_size 0 with a `supersedes` — an empty tree cannot extend anything; a "
                      "consistency proof from a later size back to zero is a truncation, not a "
                      "checkpoint")
    seen = set()
    for i, w in enumerate(doc.get("witnesses") or []):
        if w["identity"] == (doc.get("issuer") or {}).get("identity"):
            errors.append(f"witnesses[{i}]: the issuer cannot witness its own checkpoint — a "
                          f"countersignature by the signer adds no independent statement, and "
                          f"counting it would let an unwitnessed log claim to be anchored")
        if w["identity"] in seen:
            errors.append(f"witnesses[{i}]: {w['identity']!r} appears twice — one witness, one "
                          f"signature, or a witness threshold can be met by repetition")
        seen.add(w["identity"])
    return errors


def check_promotion_evidence(doc):
    """The outcome must agree with the diff, and the revision sets must actually differ.

    JSON Schema can hold the fields; it cannot check that the record is internally honest. An
    `outcome: promoted` over an unapproved diff entry is the exact artifact this record exists to
    make impossible — a promotion that reads as evidence-backed while the evidence says otherwise —
    and it is the one thing a later reader has no way to detect for themselves."""
    errors = []
    diff = doc.get("diff", [])
    unapproved = [e["output"] for e in diff if not e.get("approval")]
    computed = "refused" if unapproved else "promoted"
    stated = doc.get("outcome")
    if stated and stated != computed:
        errors.append(f"outcome: states {stated!r} but the diff computes {computed!r}"
                      + (f" — unapproved: {unapproved}" if unapproved else "")
                      + ". The diff is the entire gate: empty, or every entry explicitly approved.")
    if doc.get("from_revisions") == doc.get("to_revisions"):
        errors.append("from_revisions equals to_revisions — a promotion to what is already pinned "
                      "compares a revision set with itself, so an empty diff proves nothing")
    seen = set()
    for e in diff:
        if e["output"] in seen:
            errors.append(f"diff: {e['output']!r} appears twice — one output, one verdict, or an "
                          f"approval on one entry silently covers the other")
        seen.add(e["output"])
    for v in doc.get("volatile_outputs_excluded", []):
        if v in seen:
            errors.append(f"volatile_outputs_excluded names {v!r}, which also appears in the diff "
                          f"— an output is either excluded from the comparison or compared, and "
                          f"claiming both hides which happened")
    return errors


def check_registration_verdict(doc):
    """The ceiling must actually be a ceiling.

    JSON Schema can require both lists; it cannot say one is contained in the other. And containment
    is the whole invariant: an `effective_capabilities` entry with no `approved` disposition behind
    it is authority nobody granted, which is precisely what default-deny exists to prevent. A verdict
    that merely HAS the fields is the failure mode this catches."""
    errors = []
    # A capability name that resolves to nothing is a ceiling over an empty set: it looks
    # restrictive and restricts nothing, which is worse than an absent verdict because it reads as
    # a decision.
    try:
        import yaml as _y
        _caps = _y.safe_load(open(ROOT / "taxonomies" / "provider-capability.yaml", encoding="utf-8"))
        known = {t["term"] for t in (_caps or {}).get("terms", [])}
    except Exception:
        known = set()
    if known:
        for i, a in enumerate(doc.get("capability_admissions", [])):
            if a["capability"] not in known:
                errors.append(f"capability_admissions[{i}]: {a['capability']!r} is not a term in "
                              f"provider-capability.yaml — a disposition over a capability nobody "
                              f"offers governs nothing")
        for cap in doc.get("effective_capabilities", []):
            if cap not in known:
                errors.append(f"effective_capabilities: {cap!r} is not a term in "
                              f"provider-capability.yaml")
    admitted = {a["capability"] for a in doc.get("capability_admissions", [])
                if a.get("disposition") in ("approved", "provisional")}
    for cap in doc.get("effective_capabilities", []):
        if cap not in admitted:
            errors.append(f"effective_capabilities: {cap!r} is in the ceiling but no admission "
                          f"approves it — the ceiling is declared \u2229 admitted \u2229 "
                          f"registry-enabled \u2229 matrix-permitted, so nothing can enter it that "
                          f"was not admitted")
    seen = {}
    for i, a in enumerate(doc.get("capability_admissions", [])):
        cap = a["capability"]
        if cap in seen and a.get("disposition") == doc["capability_admissions"][seen[cap]].get("disposition"):
            errors.append(f"capability_admissions[{i}]: {cap!r} repeats its previous disposition "
                          f"{a.get('disposition')!r} \u2014 the list is append-only history, and an "
                          f"entry that changes nothing records no act")
        seen[cap] = i
    return errors


def check_data_references(doc):
    """A data reference is a URF string — `uuid/<v4>[@version][?reference_data_type==<kind>]`
    (ADR-012 + identifier-scheme §9). It MUST parse, and MUST resolve to an ACTIVE reference_data
    layer of the declared kind. Enforced deterministically: a malformed URF, a dangling uuid, a
    non-active or non-reference_data target, or a reference_data_type mismatch is a FAIL. The
    advisory-name drift check is GONE with the advisory name — the URL carries identity, and a
    name that duplicated the resolved handle was a stored derivable (DRV-001)."""
    import importlib.util as _ilu, pathlib as _pl, re as _re
    _spec = _ilu.spec_from_file_location("urf", _pl.Path(__file__).parent / "urf.py")
    _urf = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_urf)
    index, errors = _reference_data_index(), []

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")
        elif isinstance(node, str) and node.startswith("uuid/") and "reference_data_type==" in node:
            loc = f"{doc.get('handle') or doc.get('uuid', '?')} at {path}"
            try:
                u = _urf.parse(node)
            except _urf.URFError as e:
                errors.append(f"{loc}: data reference is not a valid URF — {e}")
                return
            ru = u.path[1] if len(u.path) > 1 else None
            target = index.get(ru)
            if not target:
                errors.append(f"{loc}: data reference {ru} does not resolve to any reference_data "
                              f"layer (dangling reference)")
                return
            if target.get("state") != "active":
                errors.append(f"{loc}: data reference {ru} resolves to a "
                              f"{target.get('state')!r} layer — must be active")
            want = _re.search(r"reference_data_type==([A-Za-z0-9_.*-]+)", node)
            if want and target.get("reference_data_type") != want.group(1):
                errors.append(f"{loc}: reference_data_type {want.group(1)!r} != resolved layer's "
                              f"{target.get('reference_data_type')!r}")
            if u.pin and target.get("version") and u.pin != target["version"]:
                errors.append(f"{loc}: pinned @{u.pin} != resolved layer version "
                              f"{target['version']} — a pin names an immutable revision")

    walk(doc.get("fields") or doc.get("states") or {}, "")
    return errors

def _retired_identities():
    """Identities the maintainer deliberately removed, declared in `registry/renames.yaml` under
    `retired:` as `<path>#<uuid>` (ADR-051: a removal is declared, never silent). A `supersedes` may
    name one — the predecessor is documented, just no longer carried in-tree — so lineage treats it as
    resolved-and-gone rather than dangling. Type/version comparisons are skipped: there is nothing left
    to compare against, and the retirement line states what replaced it."""
    out = set()
    path = ROOT / "renames.yaml"
    if not path.exists() or yaml is None:
        return out
    for key in (yaml.safe_load(path.read_text()) or {}).get("retired") or {}:
        if "#" in str(key):
            out.add(str(key).rsplit("#", 1)[1])
    return out


def _eval_context_terms():
    """Canonical `evaluation-context` accumulator names from the policy-fact taxonomy."""
    path = ROOT / "taxonomies" / "policy-fact.yaml"
    if not path.exists() or yaml is None:
        return set()
    doc = yaml.safe_load(path.read_text()) or {}
    return {t.get("term") for t in (doc.get("terms") or [])
            if isinstance(t, dict) and t.get("parent") == "evaluation-context"}


def check_evaluation_context(doc):
    """A constraint's `constraint_type` names the accumulator it contributes to — and that is the SAME
    name a later policy reads it back under (policy-contract §7.1). That round-trip is the whole point
    of the context, and it only holds if one vocabulary serves both directions: emit `allowed_zones`,
    read `allowed_zones`. Left ungoverned it had already drifted — §7.1's prose said `zone_restriction`
    for the accumulator the taxonomy calls `allowed_zones`, two names for one thing, which is exactly
    the break this check exists to prevent."""
    if not (isinstance(doc, dict) and "request_uuid" in doc and "pass_number" in doc
            and "record_type" not in doc):
        return []
    terms = _eval_context_terms()
    errors = []
    for i, c in enumerate(doc.get("constraints") or []):
        ct = c.get("constraint_type") if isinstance(c, dict) else None
        if ct and terms and ct not in terms:
            errors.append(f"constraints[{i}]: constraint_type {ct!r} is not a canonical "
                          f"`evaluation-context` term in the policy-fact taxonomy — a policy would "
                          f"emit under one name and read back under another")
    return errors


def check_layer_lineage(doc):
    """Lineage is EXPLICIT and the single mechanism (ADR-012): `supersedes` names the uuid(s) this
    reference_data version directly supersedes. Absent = a lineage root. When present, each uuid MUST
    resolve to an existing reference_data layer of the SAME reference_data_type with a strictly LOWER
    version, and must not point at itself (or form a version cycle). `handle` is advisory and plays no
    part here — the DAG is uuid-based."""
    if not (isinstance(doc, dict) and doc.get("record_type") == "layer" and doc.get("layer_type") == "reference_data"):
        return []
    errors = []
    index = _reference_data_index()
    self_uuid, self_type, self_ver = doc.get("uuid"), doc.get("reference_data_type"), _ver_tuple(doc.get("version"))
    for sid in doc.get("supersedes") or []:
        if sid == self_uuid:
            errors.append(f"supersedes: {sid} points at itself"); continue
        prior = index.get(sid)
        if prior is None:
            if sid in _retired_identities():
                continue                          # predecessor removed by declared retirement, not missing
            errors.append(f"supersedes: {sid} does not resolve to a reference_data layer (dangling lineage link)"); continue
        if self_type and prior["reference_data_type"] and self_type != prior["reference_data_type"]:
            errors.append(f"supersedes: {sid} is reference_data_type {prior['reference_data_type']!r}, but this layer is {self_type!r} — lineage stays within one type")
        if _ver_tuple(prior["version"]) >= self_ver:
            errors.append(f"supersedes: {sid} version {prior['version']} is not lower than this version {doc.get('version')} — a superseding version must be higher")
    return errors


def _selector_covers_type(sel, rt):
    """Does a §10 `covers` selector target resource_type `rt`? Authority prefix stripped; a bare
    `*`/`**` covers all; otherwise the selector's dotted type-path must be a prefix of `rt` (broader,
    e.g. `Compute.*` covers `Compute.VM`) or `rt` a prefix of it (narrower provider, e.g.
    `Compute.VM.OCPVirt`). Deliberately lenient — the authoritative matcher is DCM's assembly engine;
    this only catches a `covers` that plainly excludes the layer's own type."""
    s = sel.strip()
    if "/" in s:                                  # strip authority (peer.dcm.east/Compute.VM.*)
        s = s.rsplit("/", 1)[1]
    if s in ("*", "**"):
        return True
    base = [p for p in s.split(".") if p and p != "*"]
    rt_parts = rt.split(".")
    return base == rt_parts[:len(base)] or rt_parts == base[:len(rt_parts)]


def check_layer_scoping(doc):
    """covers ⋈ resource_type single-source (ADR-054 reconciliation): `resource_type X` is the
    single-type shorthand for `covers ["X.*"]`, so a type-scoped layer omits `covers`. When BOTH are
    declared they MUST agree — `covers` must include the layer's own `resource_type`, else there are
    two disagreeing homes for one concept."""
    rt, covers = doc.get("resource_type"), doc.get("covers")
    if not rt or not covers:
        return []
    # covers is ONE URF filter (identifier-scheme §9). The agreement check: some
    # resource_type term in the expression must cover the layer's own type (exact or glob).
    import importlib.util as _ilu, pathlib as _pl
    _spec = _ilu.spec_from_file_location("urf", _pl.Path(__file__).parent / "urf.py")
    _urf = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_urf)
    loc = f"layer {doc.get('name', '?')} ({str(doc.get('uuid', ''))[:8]})"
    try:
        parsed = _urf.parse(covers)
    except _urf.URFError as e:
        return [f"{loc}: covers is not a valid URF filter — {e}"]
    import re as _re
    terms = _re.findall(r"resource_type==([A-Za-z0-9.*]+)", covers) +             [m for grp in _re.findall(r"resource_type=in=\(([^)]*)\)", covers) for m in grp.split(",")]
    if not terms:
        return [f"{loc}: covers carries no resource_type term — cannot agree with resource_type {rt!r}"]
    def sel_covers(sel, t):
        if sel.endswith("*"):
            return t.startswith(sel[:-1]) or (sel[:-1].rstrip('.') == t)
        return sel == t or t.startswith(sel + ".")
    if not any(sel_covers(s2, rt) for s2 in terms):
        return [f"{loc}: resource_type {rt!r} and covers {covers!r} disagree — covers must match the "
                f"layer's own type; omit covers for the derived default."]
    return []


def check_layer(doc):
    """All semantic checks for a layer record: data-reference + lineage + covers/resource_type scoping."""
    return check_data_references(doc) + check_layer_lineage(doc) + check_layer_scoping(doc)


def check_realized_entity(doc):
    """All semantic checks for a realized entity."""
    return (check_process_entity(doc) + check_provider_extensions(doc)
            + check_data_references(doc) + check_provider_preference(doc))


def check_profile(doc):
    """Profile semantic checks JSON Schema cannot express (profile.schema.json):
      (a) every `contains[].ref` and `composes[]` entry parses as a URF reference;
      (b) an `off` entry on a security-relevant artifact carries a `reason` — a disabled
          security control is a deliberate, reviewable act, never a bare absence;
      (c) NO WEAKENING ON COMPOSITION: a profile may not downgrade to `advisory`/`off` an
          entry a profile it composes marks `required` (the immutable-ceiling discipline).
          Composed profiles are resolved from the instances directory by handle."""
    import importlib.util as _ilu, pathlib as _pl
    _spec = _ilu.spec_from_file_location("urf", _pl.Path(__file__).parent / "urf.py")
    _urf = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_urf)
    errors, loc = [], f"profile {doc.get('handle', '?')}"
    SECURITY_HINTS = ("audit", "attestation", "governance", "sovereign", "credential", "policy/tenant")

    def parse_ref(ref, where):
        try:
            _urf.parse(ref)
        except _urf.URFError as e:
            errors.append(f"{loc}: {where} {ref!r} is not a valid URF reference — {e}")

    own = {}
    for entry in doc.get("contains") or []:
        ref, state = entry.get("ref", ""), entry.get("state")
        parse_ref(ref, "contains[].ref")
        own[ref] = state
        if state == "off" and any(h in ref for h in SECURITY_HINTS) and not entry.get("reason"):
            errors.append(f"{loc}: {ref!r} is turned off without a reason — a disabled "
                          f"security-relevant artifact states why (profile.schema.json contains[].reason)")
    # (c) composition may not weaken
    by_handle = {}
    for path in sorted((ROOT / "profiles").glob("*.y*ml")):
        for other in load_all(path):
            if isinstance(other, dict) and other.get("record_type") == "profile":
                by_handle[other.get("handle")] = other
    for cref in doc.get("composes") or []:
        parse_ref(cref, "composes[]")
        target = by_handle.get(cref.split("estate/", 1)[-1]) or by_handle.get(cref)
        if not target:
            continue
        for entry in target.get("contains") or []:
            ref = entry.get("ref")
            if entry.get("state") == "required" and own.get(ref) in ("advisory", "off"):
                errors.append(f"{loc}: weakens {ref!r} to {own[ref]!r}, but composed profile "
                              f"{target.get('handle')!r} marks it required — composition may not "
                              f"weaken a required entry")
    return errors


def pick_instance(doc):
    """Dispatch: `record_type` first (catalog_item ⇒ catalog item, + semantic checks);
`record_type: profile` ⇒ an activatable posture; `resource_type` ⇒ realized entity."""
    if isinstance(doc, dict) and doc.get("record_type") == "catalog_item":
        return (CATALOG_VALIDATOR,
                lambda d: f"catalog item {d['name']} v{d['version']} {d['uuid'][:8]} ({len(d['constituents'])} constituents)",
                lambda d: check_catalog_item(d) + check_constituent_edges(d))
    # A class record validates as a CLASS wherever it lives. Worked-example classes mirror the
    # class hierarchy under examples/classes/, and an example that is not checked the same way as
    # the real thing is an illustration rather than a demonstration.
    if isinstance(doc, dict) and doc.get("record_type") == "class":
        return (CLASS_VALIDATOR,
                lambda d: f"{d['resource_type']} ({d['class']} Class) v{d['version']} — "
                          f"{len(d.get('elements') or [])} element(s)",
                check_class_record)
    if isinstance(doc, dict) and doc.get("record_type") == "conformance_declaration":
        return (CONFORMANCE_DECL_VALIDATOR,
                lambda d: f"conformance declaration {d['implementation']['name']} "
                          f"v{d['implementation']['version']} — udlm {d['udlm_version']}, "
                          f"level {d['level']}")
    if isinstance(doc, dict) and doc.get("record_type") == "composition":
        return (COMPOSITION_RECORD_VALIDATOR,
                lambda d: f"composition {d.get('handle', d['uuid'][:8])} [{d.get('state')}]")
    if isinstance(doc, dict) and doc.get("record_type") == "policy":
        return (POLICY_VALIDATOR,
                lambda d: f"policy {d['name']} ({d['policy_type']}) {d['uuid'][:8]}",
                check_schedule_clauses)
    # Dispatched by SHAPE, not by record_type: an evaluation context is deliberately NOT a record —
    # no identity uuid, no lifecycle, no version of its own. Giving it a record_type to satisfy the
    # dispatcher would make the model assert something untrue about it (policy-contract §7.1).
    if isinstance(doc, dict) and "request_uuid" in doc and "pass_number" in doc and "record_type" not in doc:
        return (EVAL_CONTEXT_VALIDATOR,
                lambda d: f"evaluation_context pass {d['pass_number']} req {d['request_uuid'][:8]} "
                          f"({len(d.get('constraints') or [])} constraints)",
                check_evaluation_context)
    if isinstance(doc, dict) and doc.get("record_type") == "log_checkpoint":
        return (LOG_CHECKPOINT_VALIDATOR,
                lambda d: f"log_checkpoint {d['log_id']} @{d['tree_size']} "
                          f"({len(d.get('witnesses') or [])} witness(es))",
                check_log_checkpoint)
    if isinstance(doc, dict) and doc.get("record_type") == "promotion_evidence":
        return (PROMOTION_EVIDENCE_VALIDATOR,
                lambda d: f"promotion_evidence {d['corpus_ref'][:14]} "
                          f"{len(d['diff'])} diff entr(y/ies) -> "
                          f"{d.get('outcome') or 'unstated'}",
                check_promotion_evidence)
    if isinstance(doc, dict) and doc.get("record_type") == "registration_verdict":
        return (REGISTRATION_VERDICT_VALIDATOR,
                lambda d: f"registration_verdict {d['provider_uuid'][:8]} "
                          f"[{d['trust_posture']}] {len(d['effective_capabilities'])} effective / "
                          f"{len(d['capability_admissions'])} dispositioned",
                check_registration_verdict)
    if isinstance(doc, dict) and doc.get("record_type") == "vocabulary_term":
        return (VOCABULARY_TERM_VALIDATOR,
                lambda d: f"vocabulary_term {d['vocabulary_kind']}/{d['term']} @{d['scope']} "
                          f"[{d['curation_state']}] {d['uuid'][:8]}")
    if isinstance(doc, dict) and doc.get("record_type") == "layer":
        return (LAYER_VALIDATOR,
                lambda d: f"layer {d['name']} ({d['layer_type']}) {d['uuid'][:8]}",
                check_layer)
    if isinstance(doc, dict) and doc.get("record_type") == "audit_record":
        return AUDIT_RECORD_VALIDATOR, lambda d: f"audit_record {d['action']} {d['record_uuid'][:8]}"
    if isinstance(doc, dict) and doc.get("record_type") == "commit_log_entry":
        return COMMIT_LOG_VALIDATOR, lambda d: f"commit_log_entry seq={d['sequence']} {d['action']} {d['entry_uuid'][:8]}"
    if isinstance(doc, dict) and doc.get("record_type") == "audit_leaf":
        return AUDIT_LEAF_VALIDATOR, lambda d: f"audit_leaf idx={d['leaf_index']} {d['stage']} {d['leaf_uuid'][:8]}"
    if isinstance(doc, dict) and doc.get("record_type") == "decision_record":
        return DECISION_VALIDATOR, lambda d: f"decision_record {d.get('handle', d['title'][:24])} [{d['state']}] {d['uuid'][:8]}"
    if isinstance(doc, dict) and doc.get("record_type") == "regeneration_manifest":
        return (REGENERATION_VALIDATOR,
                lambda d: f"regeneration_manifest {d['change']['artifact']['handle']} "
                          f"[{d['classification']['compatibility']}] {d['uuid'][:8]} "
                          f"({len(d['affected_artifacts'])} affected, {len(d['consumer_debt'])} in debt)")
    if isinstance(doc, dict) and doc.get("record_type") == "finding_routing_record":
        return (FINDING_ROUTING_VALIDATOR,
                lambda d: f"finding_routing_record {d['contradicted_claim']['artifact']['handle']} "
                          f"[{d['status']}] {d['uuid'][:8]} "
                          f"({len(d['evidence']['diff_summary']['changed_outputs'])} changed outputs)")
    if isinstance(doc, dict) and doc.get("record_type") == "accreditation":
        return ACCREDITATION_VALIDATOR, lambda d: f"accreditation {d.get('handle', d['framework'])} [{d['status']}] {d['uuid'][:8]}"
    if isinstance(doc, dict) and (doc.get("term_type") == "TaxonomyTerm" or "terms" in doc):
        return (TAXONOMY_SEED_VALIDATOR,
                lambda d: f"taxonomy seed '{d.get('root', '?')}' ({len(d.get('terms', []))} terms)",
                check_taxonomy_seed)
    if isinstance(doc, dict) and doc.get("record_type") == "profile":
        return (PROFILE_VALIDATOR,
                lambda d: f"profile {d['handle']} v{d['version']} {d['uuid'][:8]} "
                          f"({len(d.get('contains') or [])} entries)",
                check_profile)
    return (INSTANCE_VALIDATOR,
            lambda d: f"{d['resource_type']} instance {d['uuid'][:8]} [{d['lifecycle_state']}]",
            check_realized_entity)


def _reverse_reference_graph():
    """Scan instances for the data-reference graph. Returns:
      nodes:     uuid -> {"label", "is_refdata"}
      referrers: target_uuid -> [referrer_uuid]   (who references target)
    This is what lets change-impact cascade TRANSITIVELY up the graph (ADR-012 #2): a record referencing
    a reference_data layer that is itself referenced, and so on — e.g. deployment → image → library."""
    nodes, referrers = {}, {}
    for subdir in ("examples", "taxonomies", "profiles"):
        base = ROOT / subdir
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if "must-reject" in path.parts:              # gate inputs, not documents (see validate_dir)
                continue
            if path.suffix not in (".json", ".yaml", ".yml"):
                continue
            for doc in load_all(path):                   # multi-doc aware (`---` streams)
                if not isinstance(doc, dict):
                    continue
                src = doc.get("uuid")
                if not src:
                    continue
                nodes[src] = {
                    "label": doc.get("handle") or doc.get("name") or src,
                    "is_refdata": (doc.get("record_type") == "vocabulary_term"
                                   or (doc.get("record_type") == "layer"
                                       and doc.get("layer_type") == "reference_data")),
                }
                for _loc, tgt in _find_data_references(doc):
                    referrers.setdefault(tgt, []).append(src)
    return nodes, referrers


def impact_report():
    """Change-impact map (ADR-012 #2): for every data reference to a version that has since been
    superseded (the explicit supersedes DAG has a newer descendant), report it — and CASCADE the impact
    transitively up the reference graph: whatever references an impacted record is itself impacted (a
    library bumped under a container image, under a deployment, ...). ADVISORY: never fails the build.
    Impact is derived data (supersedes DAG + reverse reference graph); the DECISION to act on it — bump
    dependents — is a DCM cascade policy (ADR-012 §7; DCM ADR-024), never automatic here."""
    index = _reference_data_index()
    if not index:
        return
    succ = _successor_index(index)
    nodes, referrers = _reverse_reference_graph()
    superseded = {u for u in index if _descendants(u, succ)}         # versions with a newer descendant
    direct = sorted({(s, t) for t in superseded for s in referrers.get(t, [])})
    print("== change-impact (explicit supersedes DAG; advisory) ==")

    # THE INSTRUMENT CHECKS ITSELF, and this is not the same thing as the report failing.
    # The report is advisory by design (ADR-012 §7: the DECISION to act on impact is a cascade
    # policy, never automatic here). But "no impact to report" and "the graph has no edges to
    # traverse" print the SAME line, and for months it was the second — `_find_data_references`
    # looked for the object-form reference the corpus had already left behind. A tool that cannot
    # tell you it is blind will keep reassuring you.
    #
    # So: an estate with zero impacts is fine and common. An estate whose records contain data
    # references while the graph holds no edges is a broken instrument, and that IS a hard failure —
    # it is a statement about the tool, not about the estate.
    if not referrers:
        # Counted by RAW TEXT, deliberately independent of `_find_data_references`. The first
        # version of this check called that helper to decide whether references existed — using the
        # broken finder to detect that the finder was broken, which of course reported zero and
        # passed. A detector that shares a failure mode with its subject detects nothing.
        refs_in_corpus = 0
        for subdir in ("examples", "taxonomies", "profiles"):
            base = ROOT / subdir
            if not base.exists():
                continue
            for path in sorted(base.rglob("*")):
                if path.suffix not in (".json", ".yaml", ".yml") or "must-reject" in path.parts:
                    continue
                refs_in_corpus += path.read_text(encoding="utf-8").count("reference_data_type==")
        if refs_in_corpus:
            print(f"FAIL the reference graph has NO edges, yet the corpus text contains "
                  f"{refs_in_corpus} data reference(s) — the impact graph is blind, and a blind "
                  f"graph reports '0 impacted' exactly like a healthy one")
            return "blind"
    if not direct:
        print("0 reference(s) pinned to a superseded reference_data version")
        return
    print(f"{len(direct)} reference(s) pinned to a superseded reference_data version:")
    for src, tgt in direct:
        head = max(_descendants(tgt, succ), key=lambda u: _ver_tuple(index.get(u, {}).get("version")))
        slabel = nodes.get(src, {}).get("label", src[:8])
        print(f"   {slabel} → {index[tgt]['handle']} {index[tgt]['version']} ({tgt[:8]}) "
              f"pinned; superseded by {index.get(head, {}).get('version', '?')} ({head[:8]})")
        # cascade: whatever references the now-impacted src is transitively impacted — walk up
        seen, frontier = set(), list(referrers.get(src, []))
        while frontier:
            u = frontier.pop()
            if u in seen:
                continue
            seen.add(u)
            print(f"      ↳ {nodes.get(u, {}).get('label', u[:8])} transitively impacted")
            frontier.extend(referrers.get(u, []))


def main() -> int:
    failures = 0
    print("== generated (served flat-spec projections) ==")
    failures += validate_dir(
        "generated",
        lambda doc: (TYPE_VALIDATOR,
                     lambda d: f"{d['resource_type']} v{d['version']} (conforms_to {d['conforms_to']})",
                     check_ownership_declaration))
    print("== profiles (activatable deployment postures) ==")
    failures += validate_dir("profiles", pick_instance)
    print("== taxonomies (governed vocabulary seeds) ==")
    failures += validate_dir("taxonomies", pick_instance)
    print("== examples (worked records: entities, layers, policies, audit, accreditations) ==")
    failures += validate_dir("examples", pick_instance)
    print("== classes (scoped-Class artifacts — ADR-038 / P0 substrate) ==")
    failures += validate_dir(
        "classes",
        lambda doc: (CLASS_VALIDATOR,
                     lambda d: f"{d['resource_type']} ({d['class']} Class) v{d['version']} — {len(d.get('elements') or [])} element(s)"
                               + (f" + {len(d['constituents'])} constituent(s)" if d.get('constituents') else ""),
                     check_class_record))
    if impact_report() == "blind":
        failures += 1
    print(f"\n{'FAILED' if failures else 'ALL VALID'} — {failures} invalid")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

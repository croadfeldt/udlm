#!/usr/bin/env python3
"""The entity view — the merged read model, COMPUTED from per-state records (ruling 071).

An entity is stored as one record per lifecycle state (registry/state-record.schema.json): the
consumer's intent record, the control plane's requested record, the provider's realized record, and
discovery's discovered records. Nothing writes the merged "entity as it flows through the four
states" shape; a dashboard, a person, or a gate that wants to reason about one entity asks for the
view, and this module builds it: the latest record of each state, folded into one dict keyed by the
entity's uuid, in the shape realized-entity.schema.json describes.

Every gate that used to read `record["states"]["realized"]["fields"]` off a stored document reads
the same path off a view. A document already in the folded shape (a must-reject fixture, a
self-test probe) passes through unchanged, so one loader serves both while the corpus converts.

  load_records(roots)         -> the documents under those roots, each with `_path`
  build_views(docs)           -> {uuid: view} — state records grouped by entity_uuid, folded docs as-is
  as_view(doc)                -> the view of ONE document (a state record becomes a one-record view)
  is_state_record(doc)        -> True for the four per-state kinds
"""
import glob
import os

import yaml

STATE_KINDS = {"intent_record": "intent", "requested_record": "requested",
               "realized_record": "realized", "discovered_record": "discovered"}
# the body keys that live on the record beside `fields`, and which state's record the view takes them from
_CARRIED = {
    "status": ("realized", "requested", "discovered"),
    "dependencies": ("realized", "requested"),
    "sovereignty": ("realized",),
    "correlation_ids": ("realized", "discovered"),
    "adopted_standards": ("realized",),
    "portability": ("realized",),
    "expected_observation": ("realized",),
    "process": ("realized", "requested"),
    "priced_by": ("realized", "requested"),
    "constituents": ("realized", "requested"),
    "provider_preference": ("requested",),
    "metadata": ("realized", "requested", "intent", "discovered"),
    "integrity": ("realized",),
}
_SNAPSHOT = ("fields", "outputs", "at", "time_source", "origin", "provider", "roles", "assembly", "policies")
_LIFECYCLE = (("realized", "Realized"), ("requested", "Requested"), ("intent", "Intent"), ("discovered", "Discovered"))


def is_state_record(doc):
    return isinstance(doc, dict) and doc.get("record_type") in STATE_KINDS


def load_records(roots, skip_must_reject=True, skip_classes=True):
    """Every YAML document under the roots, tagged with its repo-relative path."""
    out = []
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for root in roots:
        for p in sorted(glob.glob(os.path.join(root, "**", "*.yaml"), recursive=True)):
            parts = p.split(os.sep)
            if skip_must_reject and "must-reject" in parts:
                continue
            if skip_classes and "classes" in parts:
                continue
            try:
                docs = list(yaml.safe_load_all(open(p, encoding="utf-8")))
            except Exception:
                continue
            for d in docs:
                if isinstance(d, dict):
                    d.setdefault("_path", os.path.relpath(p, root_dir))
                    out.append(d)
    return out


def _latest(records):
    """The latest record of a state: highest record_uuid (v7 is time-ordered), `at` as a tiebreak."""
    return sorted(records, key=lambda r: (str(r.get("record_uuid", "")), str(r.get("at", ""))))[-1]


def _fold(records):
    """One view from the records of one entity."""
    by_state = {}
    for r in records:
        by_state.setdefault(STATE_KINDS[r["record_type"]], []).append(r)
    latest = {st: _latest(rs) for st, rs in by_state.items()}
    head = latest.get("realized") or latest.get("requested") or latest.get("intent") or latest.get("discovered")
    view = {"uuid": head["entity_uuid"], "entity_uuid": head["entity_uuid"], "states": {}, "provenance": {},
            "_path": head.get("_path"), "_records": list(records)}
    for k in ("handle", "tenant_uuid", "conforms_to", "resource_type", "type_version", "type_ref", "type_digest", "generation"):
        if k in head:
            view[k] = head[k]
    for st, name in _LIFECYCLE:
        if st in latest:
            view["lifecycle_state"] = name
            break
    for st, rec in latest.items():
        view["states"][st] = {k: rec[k] for k in _SNAPSHOT if k in rec}
        for path, entries in (rec.get("provenance") or {}).items():
            view["provenance"].setdefault(path, []).extend(entries)
    for key, order in _CARRIED.items():
        for st in order:
            if st in latest and key in latest[st]:
                view[key] = latest[st][key]
                break
    if "generation" in view and "realized" in latest:
        view["observed_generation"] = latest["realized"].get("generation", view["generation"])
    return view


def build_views(docs):
    """{uuid: view}. State records fold by entity_uuid; anything else is already a view and is kept as is."""
    grouped, views = {}, {}
    for d in docs:
        if is_state_record(d):
            grouped.setdefault(d["entity_uuid"], []).append(d)
        elif isinstance(d, dict) and d.get("uuid"):
            views[d["uuid"]] = d
    for uuid, recs in grouped.items():
        views[uuid] = _fold(recs)
    return views


def as_view(doc):
    """The view of one document — a state record becomes a one-record view; a folded document is itself."""
    return _fold([doc]) if is_state_record(doc) else doc


def load_views(roots, **kw):
    return build_views(load_records(roots, **kw))

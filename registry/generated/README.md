# Served class specs — generated, never edited

Every `*.json` here is compiled from one class under `registry/classes/` by
`registry/tools/generate_class_specs.py`; `groups/` holds the usage-group views. Regenerate, never
edit: GEN-001 fails CI when a file is stale, GEN-002 when a compiled spec is not conformant, and
GEN-003 when a top-level `.json` has no class that produces it. A normal regenerate deletes such a
file, so do not park another tool's output in this directory.

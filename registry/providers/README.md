# providers/ — directory structure by kind

Provider support matrices are grouped into one subdirectory per **`provider.kind`**, lowercased
as declared in the document — `service/`, `information/` (and `composite/` when one exists).
The rule is deterministic: the directory is derived from the document's own `kind` field, never
chosen.

Filenames are unchanged by the grouping — only directories were added. Location is navigation,
not identity; discovery is recursive (`registry/tools/validate.py`,
`tests/check_provider_contracts.py`), so a new kind directory needs no tool change.

Any path rename ships with an old → new map in [`../renames.yaml`](../renames.yaml) — the
rename-map discipline (see `../resource-types/README.md` for the full statement).

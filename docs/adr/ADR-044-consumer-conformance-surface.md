# UDLM ADR-044: Consumer conformance surface — consumers declare what they read, the registry gates on it

**Status:** Proposed (croadfeldt upstream)
**Date:** 2026-07-25
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)
**Related — the complete picture, each cited once.** The validation program this belongs to (dav
`docs/data-model-validation-design.md` — the model, not the architecture, is the primary
validation target), the gate pattern it copies (the type-standard baseline ratchet in
`tests/check_type_standard.py` — every state green or red, drift is a conscious commit), and the
incident that motivated it (the control-plane servicetype generator mapping 5 of 46 registry
types with no warning for the rest — found by sweep, not by CI).

## Context

The registry's gates prove the model self-consistent, but the model exists to be read. Its
consumers — generators, estate CI, graph ingest, MCP servers, the analysis engine — each depend
on some slice of the registry's types, versions, and vocabularies, and none of that dependency
is recorded anywhere the registry can see. The failure mode is silent: a type rename, a version
bump, or a vocabulary change leaves every downstream reader compiling happily against a shadow
of the registry that no longer exists. The sweep that found the generator gap found it by
reading code, which does not scale and does not repeat.

## Decision

Consumers declare their read surface in `registry/consumers/*.yaml`: one manifest per consumer,
listing the resource types (with the registry version last verified against), or
`consumes_all_types: true` for envelope-level consumers. A CI gate
(`tests/check_consumer_conformance.py`) enforces three invariants: every declared type exists;
no declared version is ahead of the registry; every registry type is either consumed by at
least one manifest or explicitly acknowledged in `registry/consumers/unconsumed.yaml`, which
the gate regenerates and compares so the acknowledgment can never drift silently.

Manifests begin at `coverage: declared` — the registry records what consumers say they read.
`coverage: verified` is reserved for consumers that gate their own conformance in their own CI
against their manifest; promoting a manifest is that consumer's act, not the registry's.

## Consequences

- A breaking registry change now fails in the registry's own CI naming the consumers it breaks,
  instead of failing later in each consumer's runtime.
- The unconsumed list is a standing work queue: a type no consumer reads is either ahead of its
  adopters or dead weight, and the registry can now tell which.
- The manifest is self-reported until a consumer verifies it; a stale manifest is a defect in
  the consumer's contribution, visible in review, not an invisible omission.
- Cost: one small YAML file per consumer, updated when their read surface changes — the same
  discipline the standards-adoption register already applies to standards.

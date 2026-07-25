# class-versioning — how class inheritance evolves, pins, and proves itself

Nine cases probing the scoped-Class system's evolution contract before it is ruled: what a
Base Class change does to everything built on it, where version pins are legal, and how
blue/green typed-output diffing turns unpinning into a tested act. Mixed semantics: 001, 003,
005, and 007 are expected to work; 002, 004, 006, 008, and 009 succeed only if the system
**refuses** (the must-reject convention — refusals typed, actionable, audited).

The family encodes candidate rulings the ADRs will settle, so a gap analysis over it measures
the decisions, not just the mechanics: intra-registry references are by handle with the
registry ref as the only internal pin (004); organizational pins are uuid-precise, honored
completely, and visible as enumerated debt (005, 006); compatibility claims are promoted on
typed-output evidence, not trust (007, 008); and portability is part of the compat contract —
narrowing an element's scope is breaking even when no schema shape changes (009). Cases
010–012 carry the provenance contract (ADR-045 §7): generated specs declare their full
compilation chain (classes, layers, schemas, generator) and realized instances their provider
definition revision — live, historically reconstructible, and verified by recompilation with
mismatches refused. Cases 013–015 carry provider versioning (ADR-045 §8): internal
changes past the naturalization boundary are free (provable by empty output diff), declared-
surface changes classify and version under the standard rules, and under-declared surface
changes are refused naming the dropped output and its bound consumers.

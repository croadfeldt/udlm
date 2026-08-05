# Identity Escrow — identity state that survives re-realization (`ESC-*`)

**What this owns.** The normative rules for `Access.IdentityEscrow`
(`registry/classes/access/access/identity-escrow.yaml`): the contract for identity state that
must survive its host entity's re-realization. This file is the single home of the `ESC-*`
rule family (`registry/rule-id-registry.yaml`).

## The problem, plainly

Some machines are wiped and rebuilt as a matter of routine — a seasonal re-image, a hardware
swap, a rebuild from intent. Most of what is on the disk *should* die: that is the point of
rebuilding from intent. But a narrow class of state must not: identity the outside world
already knows — a remote-access enrollment, an application session, a device certificate.
Losing it silently turns a routine rebuild into an identity incident; keeping it ad hoc (an
operator's USB stick, a wiki page) is the failure mode the model exists to replace.

The existing pieces almost cover it. `Security.CredentialRef` carries the custody leg — a
reference to material held by an issuer, the value never in the model, the reference's
lifecycle already decoupled from any one consumer. The rehydration doctrine
(`docs/spec/foundations/four-states.md` — adoption and re-provisioning preserve the entity UUID) makes
"the same machine, rebuilt" a stable identity. What no type carried was the **contract**:
which items are captured, when, restored when, and what refuses if restore fails. That
contract is `Access.IdentityEscrow`; these are its rules.

## Rules

| Rule | Statement |
|---|---|
| `ESC-001` | An escrow binds to its host's **entity UUID** via a soft `binds_to` edge — never `contained_by` (which would cascade decommission), and never to a realization generation. Re-provisioning preserves the entity UUID, so survival across re-realization is structural, not procedural. |
| `ESC-002` | **Restore is part of converge.** A re-realization of a host with a bound escrow does not reach Converged while any `required: true` item is unrestored. The failure is typed and visible (the `restore_verified` / `items_restored` outputs are the evidence); re-imaging is never *refused* for having an escrow — it is gated on completing one. |
| `ESC-003` | **Identity is explicit, never inferred.** Minting a new entity (the unknown-device onboarding path) MUST NOT bind an existing escrow; an escrow attaches to a new entity only by an explicit, audited transfer (ESC-004). A device can therefore never silently claim another device's identity. |
| `ESC-004` | Decommissioning an entity with an active escrow requires an explicit, audited **disposition** per item: `destroy` (the escrow store destroys the material) or `transfer` (re-bind to a named successor entity). Silent orphaning of escrowed identity is refused. |
| `ESC-005` | `escrowed_items[]` is the **exhaustive survival allowlist**: identity state not listed does not survive re-realization — the wipe default is deletion. One list answers "what persists on this box", legibly. |

## Boundary notes

- **Custody is the CredentialRef's** (`docs/spec/governance/credentials.md` — the value never enters the
  model, audit, source control, or logs). The escrow adds obligations *about* the reference —
  capture-on, restore-on, required — it never re-carries material or custody semantics.
- **The ADR-008 peer test** (computed/negotiated/executed → DCM): *which* provider performs
  capture and restore, and how, is implementation. UDLM carries the contract (the items, the
  moments, the gate) and the typed evidence outputs; any conformant engine may execute it.

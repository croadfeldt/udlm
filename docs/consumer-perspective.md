---
Document Status: 📋 Draft — Initial Specification
Document Type: Consumer/User Narrative
Established: 2026-05-26
Maps to: UDLM consumption
---

# UDLM Consumer Perspective — the Driver's Handbook

> This is the consumer-side companion to DCM's `architecture/operator-perspective.md`
> (the operator's manual). Together the two perspectives cover the system from
> both sides — the **consumer** who submits intent and waits for realized state,
> and the **operator** who runs the platform that makes realization happen.

This document is for people who **use** a UDLM-conformant system. Not implement
it (that's the operator perspective in DCM); **consume** it as a user, tenant,
service owner, or peer.

---

## 1. Mental model — what UDLM is, from the outside

A UDLM-conformant system is something you give **intent** to and that gives you
**realized state** back. You declare what you want; the system manages how it
happens. The contract between you and the system is wire-compatible: any
conformant peer can read what you submit and report results in a format any
other conformant peer can read.

The driving analogy: UDLM is the **rules of the road** — what destinations exist,
what your vehicle must carry, what licenses you must hold, what signals mean.
DCM (or any peer realization) is the **road and the cars and the DMV**. You're
the driver. You don't need to know how the asphalt was poured; you need to know
where you're going, what you're allowed to ask for, and how to read the signs.

What this gets you:

- **Portability of intent.** The intent you submit to one conformant realization
  can be submitted to another. Your declarations aren't tied to a specific
  vendor's runtime.
- **Predictable lifecycle.** Every resource passes through the same four states
  (intent → requested → realized; discovered runs alongside as ground truth).
  You know what state your stuff is in, regardless of who runs the platform.
- **Federation by default.** If your data needs to flow to a peer realization
  (different team, different region, different vendor), the wire format means
  it just works — no adapters.
- **Auditability.** Every change is recorded against a tamper-evident chain.
  You can prove what you asked for, when, and what the system did with it.

What this does NOT promise:

- That every realization performs the same. DCM and a peer might both be
  conformant but have different latency, scale, or operational ergonomics.
- That every realization implements every optional contract. A realization
  with `level: "partial"` conformance excludes some contracts (e.g., maybe no
  scheduled requests, or no brownfield ingestion). Check the conformance
  declaration before depending on a feature.

---

## 2. What you submit

You submit **intent**. Intent is a declaration of what you want — not how to
build it. Concretely, intent takes the form of:

- A **request** referencing a resource type or composite service
- The **fields** the resource type requires (or accepts as optional)
- Any **scoping** — tenant, location preferences, scheduling, dependencies
- Any **policies** that should apply (e.g., declared accreditation level)

You do NOT specify:

- Which provider should fulfill the request (the realization picks based on capability)
- How the resource is implemented (provider's choice)
- Internal IDs, audit UUIDs, sequencing — the realization assigns these

The wire format for requests is part of the substrate. Every conformant peer
accepts the same request shape. See
[`entities/resource-service-entities.md`](../entities/resource-service-entities.md)
for the entity model your requests target.

---

## 3. What you get back

After you submit intent, you get back:

- A **request UUID** identifying your submission (immutable, globally unique)
- A **handle** you supplied (or one assigned) for human-friendly reference
- **Events** as the request progresses through the lifecycle states
- An **entity** (or entities) once the request is realized

Lifecycle progression you can subscribe to via events:

```
submitted → intent_captured → layers_assembled → policies_evaluated
   ↓
[requires_approval if score routes there]
   ↓
approved → placement_complete → dispatched → realized
                                                ↓
                                         (or failed at any step)
```

The full event catalog is in
[`contracts/event-catalog.md`](../contracts/event-catalog.md). Subscribe to the
ones that matter to your workflow.

Drift detection runs alongside — if the realized state diverges from intent,
`drift.*` events fire. You can subscribe to those too.

---

## 4. Identifying things — what UUIDs and handles mean

Everything in UDLM has a **UUID** (globally unique, immutable) and optionally a
**handle** (tenant-scoped, mutable, human-friendly). Rules of the road:

- Use UUIDs in code. They're stable forever.
- Use handles in UI and human conversations. They can change (with audit).
- When peers exchange data, UUIDs travel. Handles get rebound on the receiving
  side (e.g., importing a peer's entity preserves the UUID; the receiving peer
  may assign its own handle).
- Never assume a UUID will be reassigned. Reassignment is a contract violation.

See [`contracts/identifier-scheme.md`](../contracts/identifier-scheme.md) for the
full identifier contract.

---

## 5. Time — what timestamps mean and skew tolerance

All timestamps you see on the wire are **UTC, ISO 8601, millisecond precision**.
Examples: `2026-05-26T14:32:18.456Z`.

If you submit a `not_before` time for a scheduled request, use UTC. If you
submit a timestamp from a provider callback, use UTC. The realization will
reject anything else.

Skew tolerance between you and the realization is **±5 seconds**. If your
clock is more than 5 seconds off, you'll see `validation.timestamp_skew_exceeded`
errors. Run NTP.

See [`contracts/time-and-clock.md`](../contracts/time-and-clock.md).

---

## 6. Errors — how to read them and what to do

Errors come back in a closed wire envelope:

```json
{
  "error_code": "validation.scope_not_recognized",
  "message": "Scope 'tenant-foo' is not recognized.",
  "request_id": "f3b64dda-...",
  "audit_uuid": "a1b2c3d4-...",
  "retryable": false,
  "retry_after_seconds": null,
  "details": { ... },
  "timestamp": "2026-05-26T14:32:18.456Z"
}
```

The two fields you act on most:

- `error_code` — a stable identifier in a closed vocabulary
  (see [`contracts/error-model.md`](../contracts/error-model.md)). Match on this
  in code, not on `message` (messages may be localized).
- `retryable` — boolean. If `true`, you may retry after the suggested delay. If
  `false`, retrying won't help; fix the underlying condition.

Other useful patterns:

- `audit_uuid` links to a full audit record. When you file a support request,
  send the audit UUID — operators can look up the full context.
- Errors are categorized by namespace (`auth.*`, `validation.*`, `lifecycle.*`,
  `rate_limit.*`, etc.). Use namespaces to route errors in your code (e.g., all
  `rate_limit.*` errors go through your backoff path).

---

## 7. Retries — when and how

Retry rules:

1. Only retry errors with `retryable: true`.
2. Honor `retry_after_seconds` as a minimum wait.
3. **Reuse the original `Idempotency-Key`** on every retry. This is how the
   realization deduplicates and avoids creating duplicate effects.
4. Use exponential backoff with jitter: base 1s, multiplier 2, max 60s, max 5 attempts.
5. The deduplication window is at least 24 hours from your first submission.

If you reuse an `Idempotency-Key` with a different payload, the realization
will reject it with `validation.idempotency_key_mismatch`. Treat your
idempotency keys as bound to a specific request payload.

See [`contracts/retry-semantics.md`](../contracts/retry-semantics.md).

---

## 8. Rate limits — how to read 429 responses

Conformant realizations rate-limit. When you exceed a limit, you get:

- HTTP status `429 Too Many Requests` (HTTP transport)
- Error code `rate_limit.exceeded`
- `retry_after_seconds` indicating when capacity returns
- `Retry-After` HTTP header on HTTP transports

Two ways to be a good citizen:

1. **Reactive**: honor 429s and back off as instructed.
2. **Proactive**: discover the realization's rate-limit declarations via the
   capability endpoint (`GET /.well-known/udlm/schema-bundle` exposes them),
   then plan your request rate to stay below limits.

If you cross **warning** or **critical** soft thresholds (typically 75% / 90%
of limit), the realization MAY return an `X-Capacity-Level` advisory header.
Use it to slow down before you hit the hard limit.

See [`contracts/rate-limit-and-backpressure.md`](../contracts/rate-limit-and-backpressure.md).

---

## 9. Schemas — how to interpret peer data

If you receive data from a peer realization (federation, brownfield ingestion,
import), the data may contain types you don't know natively. The substrate
provides **schema sharing** so you can learn:

1. Identify the source peer (from data provenance).
2. Fetch the source peer's schema bundle at
   `GET /.well-known/udlm/schema-bundle`.
3. Locate the schema for the unknown type.
4. Validate the data against the schema.

Your realization should do this automatically. If you're building a consumer
that needs to interpret peer data directly, the contract is in
[`contracts/schema-sharing.md`](../contracts/schema-sharing.md).

---

## 10. Conformance — how to know what a realization supports

Before depending on any non-trivial feature of a realization, check its
conformance declaration:

```
GET /.well-known/udlm/conformance
```

What you'll see:

- `udlm_version` — which major version of UDLM the realization conforms to.
  You're compatible if you target the same major.
- `level` — `full` or `partial`. If partial, the `exclusions` field tells you
  which contracts the realization does NOT implement. Don't depend on those.
- `interop_surfaces` — which surfaces (consumer API, provider callbacks,
  federation, audit export) are available and how to reach them.
- `independent_verification` — if present, an independent verifier (e.g., DAV)
  has validated. More trust than self-certification alone.

A realization that excludes, say, `scheduled-requests` will reject your
scheduled-request submissions with `conformance.feature_not_implemented`. Check
the declaration so you don't waste time submitting things that will be rejected.

See [`CONFORMANCE.md`](../CONFORMANCE.md).

---

## 11. Common patterns — recipes

### 11.1 "I want to provision a VM"

1. Identify the resource type for VMs in the realization's catalog
   (`Compute.VirtualMachine` typically).
2. Submit a request with required fields (size, image, network, location).
3. Subscribe to `request.*` and `entity.*` events for your request UUID.
4. Wait for `request.realized`. The payload includes the entity UUID and the
   provider-returned fields (IP, VM ID, etc.).
5. From then on, query the entity by UUID for status, drift, etc.

### 11.2 "I want N things at once with ordering"

Use a **request dependency group**. Submit multiple requests with `wait_for`
clauses pointing at each other. The realization holds dependent requests in
`PENDING_DEPENDENCY` until the things they wait for reach the declared state
(`acknowledged`, `approved`, `dispatched`, or `realized`).

See [`lifecycle/request-dependency-graph.md`](../lifecycle/request-dependency-graph.md).

### 11.3 "I want to schedule something for later"

Use a **scheduled request**. Submit with a `scheduling` block:

```yaml
scheduling:
  mode: at | window | recurring
  not_before: <ISO 8601 UTC>
  not_after: <ISO 8601 UTC>      # optional
  recurrence: <cron expression>  # for mode: recurring
```

The request stays in `SCHEDULED` state until activation time. If the
realization excludes scheduled requests, you'll get `conformance.feature_not_implemented`.

See [`lifecycle/scheduled-requests.md`](../lifecycle/scheduled-requests.md).

### 11.4 "Something I submitted got rejected"

Read the error:

- `validation.*` → your submission was malformed; fix the payload.
- `authz.*` → you don't have permission; check your scopes.
- `policy.*` → a policy denied your request; the `details` field names the
  policy and reason.
- `rate_limit.*` → you're submitting too fast; back off.
- `lifecycle.*` → invalid state transition (e.g., trying to cancel a request
  that's already terminal).
- `conformance.feature_not_implemented` → the realization doesn't support
  this feature; check its conformance declaration.

The `audit_uuid` in the error lets you (or an operator) find the full audit
record for support follow-up.

### 11.5 "Something I created drifted"

If realized state diverges from intent (someone changed the provider's reality
out of band, hardware failure, etc.), a `drift.*` event fires. The drift
record points at the original intent and the discovered state. Decide:

- **Accept the drift**: update intent to match reality.
- **Reconcile**: submit a remediation request to drive reality back to intent.
- **Investigate**: pull the audit chain to find when and why it diverged.

See [`lifecycle/operational-models.md`](../lifecycle/operational-models.md).

---

## 12. Troubleshooting — quick triage

| Symptom | Likely cause | What to check |
|---|---|---|
| Request stuck in `PENDING_APPROVAL` | Requires a tier approval | Check the `approval.*` events; an approver needs to act |
| Request stuck in `PENDING_DEPENDENCY` | Dependency hasn't reached declared state | Check the requests it's waiting on |
| Repeated `rate_limit.exceeded` | You're hot-looping | Add jitter; honor `retry_after_seconds`; check rate-limit declarations |
| Repeated `validation.timestamp_skew_exceeded` | Clock skew | Run NTP; check your timestamps are UTC |
| `conformance.feature_not_implemented` on a feature you need | Realization doesn't support it | Read the conformance declaration; pick a different realization OR change your approach |
| Realized state never arrives, no failure event | Provider may be stuck | Check `entity.*` events; an operator may need to investigate |
| Errors with `message` you can't interpret | Localization mismatch | Match on `error_code`, not `message`; codes are normative |
| Audit query returns nothing for a UUID | Wrong tenant scope or audit retention expired | Check tenant; check retention policy in the realization's docs |

---

## 13. Where to read next

Once you've absorbed this perspective, the substrate docs you'll reach for most:

1. [`foundations/four-states.md`](../foundations/four-states.md) — the lifecycle
   in detail
2. [`entities/resource-service-entities.md`](../entities/resource-service-entities.md) —
   the entity model
3. [`contracts/event-catalog.md`](../contracts/event-catalog.md) — what events
   you can subscribe to
4. [`contracts/error-model.md`](../contracts/error-model.md) — the full closed
   error vocabulary
5. [`foundations/examples.md`](../foundations/examples.md) — worked examples
   of the lifecycle in action
6. [`CONFORMANCE.md`](../CONFORMANCE.md) — what conformance means and how to
   verify it

For the operator side (running a realization), see DCM's
`architecture/operator-perspective.md` at
[github.com/dcm-project/dcm](https://github.com/dcm-project/dcm).

# UDLM ADR-083: A log shipper binds a log store, in the terms the syslog and OpenTelemetry standards already use

**Status:** Accepted (croadfeldt upstream) — requires engineering ratification; maintainer decision 2026-10-10
**Realized by:** `registry/classes/resource/observability/log-shipper/_base.yaml` (0.8.0) · `registry/classes/resource/observability/log-shipper/syslog.yaml` · `registry/classes/resource/observability/log-shipper/otlp.yaml` · `registry/classes/resource/data/log-store/_base.yaml` · `registry/generated/log-store.json` · `registry/standards-adoption-register.md` § Observability
**Date:** 2026-10-10
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)

**Background — read first (the cold reader's on-ramp; skip if you have the context).**
`class-tiers.md (CLS-001..013) — three tiers: a Base any member can realize, a Type spent on one axis (form or dialect), a Provider Class only for provider-specific data; usage-group filing is separate from the hierarchy`.
`ADR-082 — a class is defined once and filed under usage groups like hard links; LogShipper lost its Observability folder and is filed under observability`.
`registry/edge-types.yaml — binds_to borrows another record's published output across a boundary; contained_by says a record is part of another`.

---

## Context

A deployment wants every machine, device and cluster to send its logs to one central store, and wants that
to be a checkable fact rather than a pile of agent configs. `LogShipper` (0.7.2) was meant for this, but it
falls short in four ways:

- **Its source and destination are strings.** The source is a hostname and the destination a URL, so a
  shipper can't be followed to its machine's record, and moving the store means editing every shipper.
- **It only knows hosts.** Appliances, BMCs and switches send their own syslog, and a cluster forwarder ships
  container and audit logs. None of these has a hostname to put in the string.
- **It has no protocol.** The sink is described as an OTLP URL, but most senders in a real estate speak
  syslog, and the two need different settings.
- **The store has no class.** Retention, intake and who may read the logs have nowhere to be declared.

Mature standards already cover most of this. RFC 9742 (2025) is the IETF's data model for syslog
configuration: a remote destination, its transport, and a filter by facility and severity. Redfish
EventDestination (for BMCs) and OpenConfig system-logging (for switches) express the same thing. The
OpenTelemetry semantic conventions name the identity a log line carries (`host.name`), and OTLP is the
other intake protocol.

## Decision

**A log shipper binds a log store, and is written in the terms of those standards.** In practice: one
`LogShipper` record per source, pointing at the source and at the store; the store publishes its intake, and
the shipper borrows it.

- **`LogShipper` (Base, 0.7.2 → 0.8.0, breaking).** The source becomes a `contained_by` edge to a `Machine`,
  `BMC`, `NetworkSwitch`, `NetworkGateway` or `KubernetesCluster`. The destination becomes a `binds_to` edge
  to a `LogStore`, borrowing its published `intake_endpoints`. `source` gains `native`, `containers` and
  `audit`. New `min_severity` uses RFC 5424 names with RFC 9742's "this level and above". `labels` are
  OpenTelemetry resource attributes, and the provider always stamps `host.name` and `udlm.handle`.
- **The Type tier is the wire protocol (a dialect, CLS-004).** `LogShipper.Syslog` adds `transport`
  (RFC 9742's `udp`/`tls`, plus Redfish's `tcp`/`relp`), `format` and `facilities`. `LogShipper.OTLP` adds
  `protocol` and `compression`, as the OTLP exporter configuration names them.
- **`LogStore` is a new Base** (0.1.0): `retention_days`, the `intake` it must offer (protocol + transport),
  and `readers` as a `references` edge to `Grouping`. It publishes `intake_endpoints`.
- **No Provider Classes.** An rsyslog role, a Redfish EventDestination, a device setting and a cluster
  forwarder all realize a Type with no data of their own (CLS-005).
- **Filing:** `LogShipper` stays under `observability`. `LogStore` is filed and hosted under `data`, beside
  `Database`, because it is a managed data service.

Both pass the Base test (CLS-002). (a) RFC 9742, Redfish and OpenTelemetry each treat "send this system's
logs, filtered, to a collector" as one thing, and every log store accepts syslog or OTLP. (b) Each Base
element is honorable by every sender or store. (c) An order at `LogShipper` is fillable by either Type.

## Alternatives considered

- **Keep strings for source and sink.** Rejected: nothing could check coverage against the estate, and a
  store move touches every shipper.
- **Split the Type tier by form (host agent versus device-native).** Rejected: the split adds no elements;
  `source: native` says it. The protocol is where the elements actually differ.
- **Model the sender's configuration (rsyslog, OpenTelemetry Collector or cluster-forwarder YAML).**
  Rejected: that is mechanism, and it belongs to the provider. The record states the outcome.
- **Query on `LogStore`.** Rejected for now: no query standard spans stores (LogQL, Elasticsearch and others
  differ), so a query element would be one product's.
- **Rename `LogShipper`.** Not taken: no standard offers a better noun, and the class keeps its identity.

## Consequences

- **Easier:** coverage is computable (a realized machine with no `LogShipper` is a gap a deployment can
  alert on), a store move is one record, and a log line resolves to its record through `udlm.handle`.
- **Harder:** 0.8.0 is breaking. A 0.7.2 record must be rewritten: `target.host` becomes a `contained_by`
  edge, and `sink.url` becomes a `binds_to` edge to a `LogStore`.
- **"Exactly one source edge" is prose.** It is stated on the edges but no gate enforces it yet.

## Data · Policy · Provider

- **Data:** the four classes above; the store's intake and each shipper's edges are the whole record.
- **Policy:** whether every resource must have a shipper, the staleness bound on `last_shipped_at`, and
  retention minimums. Checking that a shipper's protocol and transport appear in the store's intake is
  admission.
- **Provider:** which product stores the logs, and how each sender is configured.

**Peer test (ADR-008):** could a conformant peer shape the shipper-to-store record differently and still
interoperate? No; the edge and the published intake are what let any provider realize any shipper, so they
belong to the substrate. Which agent ships and which store keeps are the providers' choice.

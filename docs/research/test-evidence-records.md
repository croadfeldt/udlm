# Test evidence as UDLM records

**What this is:** a proposal to record what an automated test proved about a software package as
UDLM Knowledge records, with the signed attestation as a projection of the record rather than a
separate document. It comes from the AI Test Harness, which already produces this evidence on real
code, and it is the first concrete producer of the SLSA-shaped records issue #558 asks for. It is
written for review; the decisions it needs are at the end.

**Status:** research. Two proposed classes and six worked records are in this change, validating
against the registry. Nothing is applied to any estate.

## The problem

When a dependency changes, the harness writes tests, runs them in a sealed sandbox against the old
and the new version, and reports what it proved: this vulnerability is closed, that downgrade opens
one, this package is exposed today. Today that evidence lives in the harness's own files: a record
per test, an in-toto statement signed over the records, and a draft VEX statement per vulnerability.
It is traceable, but it is the harness's shape, and nothing else can read it, reference it, or
verify it by the rules the rest of the estate uses.

UDLM already has the rules: one record per lifecycle state, provenance per field, a tamper-evident
head on each record chained to its predecessor, a Merkle audit log, and knowledge records for
vulnerabilities and packages. What it lacks is a record for the evidence itself and a signed
projection of a record that an outside verifier can check. This proposal supplies both.

## What the harness produces, and where each part lands

| Harness output | UDLM home |
|---|---|
| One record per accepted test: file, digest, category, what it targets, how it was validated | `TestEvidence`, a new Knowledge base class |
| The package and vulnerability the test is about | References to the existing `SoftwarePackage` and `Vulnerability` records, which the harness also produces as a provider of knowledge |
| The run: model, prompt digest, tool versions, sandbox image | A `Job` record; the evidence references it and repeats none of it |
| The draft VEX statement per vulnerability | `VexStatement`, a new Knowledge base class; status is OpenVEX's codelist by reference |
| Findings with a class and a confidence | Sealed findings on the ledger (`udlm-finding` facet), never a record of their own |
| The signed in-toto statement | Adopted by reference on `TestEvidence`; its subject digest is the realized record's integrity head |

The lifecycle maps onto the Knowledge family's curation reading of the four states, so it is not a
field: a candidate the generator proposes is an intent record; one under review is a requested record;
a test a reviewer accepts is a realized record, with `scope` on it saying overlay or standard suite; a retired test is a deprecated
record with its reason. Every change is a new record naming its predecessor.

## How a consumer verifies a claim

1. Check the signature on the DSSE envelope.
2. Read the statement's subject digest and find the `TestEvidence` realized record whose
   `integrity.head` equals it. The head is computed by `registry/tools/integrity_chain.py`, so the
   harness calls that code rather than its own.
3. Walk `supersedes` back through the record's history if the claim depends on it.
4. Follow `job_ref` for how the test was produced, `software_package_ref` and `vulnerability_ref` for
   what it is about, and `vex_statement_ref` for the claim it supports.

The join runs one way, from the statement to the record. The record carries nothing about the
statement, because the head it is verified against covers the whole record.

## What the worked records show

All six are under `registry/examples/`, from one real run of the harness on a FastAPI application's
dependency-fix pull request:

- `example-vulnerability-cve-2024-33664.yaml`: the vulnerability, one discovered record, observed by
  the harness as a discovery source.
- `example-software-package-python-jose.yaml`: the package version, one record per purl.
- `example-job-ai-test-harness-run.yaml`: the run, requested and realized; the model and tool
  versions are its results.
- `example-test-evidence-records.yaml`: the test that proved the vulnerability fixed, as its
  candidate (intent), its reviewer's queue entry (requested), and its accepted (realized, overlay)
  record, sealed.
- `example-vex-statement-cve-2024-33664.yaml`: the draft statement, `fixed`, resting on that test;
  only Product Security's realized record would make it confirmed.

The harness side of this is in `croadfeldt/ai-test-harness`: the attestation stage would emit these
records and compute the head with UDLM's canonicalization, and the packet would cite the record
uuids.

## What this changes for SLSA

Issue #558 asks for our records to be SLSA records. With this, a realized `TestEvidence` record is the
thing a SLSA-style attestation is about: the in-toto statement's subject is the record's own head,
the predicate is the vetted test-result type, and the producing `Job` is where the build-like
provenance lives. The standards register can move SLSA and in-toto from a referenced pattern to
adopted, with `TestEvidence` as the first adopter and `adopts` entries on the class pinning the
versions.

## Decisions for the maintainer

1. **Accept `TestEvidence` and `VexStatement` as Knowledge base classes** at version 0.1.0, status
   proposed until the harness emits real records against them.
2. **Confirm the lifecycle mapping**: candidate = intent, accepted and standard = realized with
   `scope`, retired = deprecated. No fifth state, no lifecycle field.
3. **Confirm the enums stay on the classes** (category, differential, role, scope) as closed sets the
   producer owns, and that OpenVEX's status is carried by reference and not minted as a vocabulary.
4. **Confirm the join direction**: the statement subject is the record head, and the record carries
   nothing about the statement. If a reverse pointer is wanted, it belongs on the ledger seal, not on
   the record.
5. **Rule ids**: assign ids in a registered family for the two new classes' rules, or say which
   existing family (Knowledge, INT) they fall under.
6. **Move SLSA and in-toto in the standards register** from pattern to adopted, with `TestEvidence`
   named as the first producer, closing or narrowing #558.

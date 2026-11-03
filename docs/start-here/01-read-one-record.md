# Step 1 — read one record

Open [`registry/examples/example-vm-app01-realized-record.yaml`](../../registry/examples/example-vm-app01-realized-record.yaml).
It is what a provider wrote after it built a VM called `app-01`. Read it top to bottom with this
key beside it. Nothing to type yet.

## The envelope — the same on every record

| Field | What it is |
|---|---|
| `record_type`, `state` | which of the four records this is: here `realized_record`, state `Realized` |
| `entity_uuid` | the thing's identity, for life; every record about this VM carries the same one |
| `record_uuid` | this record's own identity; time-ordered, so records sort by when they were made |
| `tenant_uuid` | who owns the thing |
| `resource_type`, `type_version`, `type_ref` | the class this record follows, pinned to one version |
| `conforms_to` | which UDLM spec version the record follows |
| `handle` | a readable name; advisory, never used to resolve anything |
| `at`, `time_source` | when, and whose clock said so |
| `origin` | how the record came to be: declared by someone, derived from a scan, or back-filled |
| `provider` | who built it |
| `generation` | which version of the intent this fulfils |

## The body — what this record says

| Field | What it is |
|---|---|
| `fields` | the VM as built: `cpu`, `memory`, `disks`, `networks`, `guest_os`, `firmware`, `run_state` |
| `outputs` | what the provider reports back and others can bind to: the IP, the hostname, the MAC |
| `dependencies` | the edges: the host it sits on, the volume it uses, the address it holds |
| `correlation_ids` | how to recognise this VM in a provider's own terms, such as its libvirt domain uuid |
| `status` | the provider's conditions, such as `Ready` |
| `sovereignty` | where it may run and what classification it carries |
| `adopted_standards` | which external standard shaped this record, and at what version |
| `portability` | whether this record could be re-realized by a different provider |
| `expected_observation` | how often a scan should find it, and what to do if one doesn't |
| `provenance` | which actor or policy set each field, and when |
| `requested_ref`, `requested_ref_head` | the request this fulfils, and a hash so the link can be checked |
| `supersedes` | the record this one replaces: records are never edited |
| `integrity` | a hash chain over this record's versions, so tampering shows |

## Done when

You can read `fields.cpu.count: 4` and say "that is what was built", read
`outputs.primary_ip` and say "that is what came back", and read `supersedes` and say "the old
version is still there, this one replaced it".

Next: [Step 2 — say what you want](02-say-what-you-want.md).

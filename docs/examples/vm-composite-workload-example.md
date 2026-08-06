# Worked example: a single-VM workload as a Composite — VM, address, derived DNS, day-0 job

**What this settles:** how a complete small workload — one VM on an isolated segment with a
static address, DNS records, and a post-provision job — is authored as intent. The source
material is a real, working provisioning playbook (anonymized): ~200 lines of imperative
shell across three plays. The intent document below carries the same workload in ~60 lines,
and improves on the playbook in three places the comparison table calls out.

The workload: a game-server VM on a DMZ segment. 8 vCPU, 32 GiB, one 128 GB disk, a current
Fedora Server guest, a static address on an isolated VLAN the host itself holds no address
on, forward and reverse DNS, and a first-boot job that grows the root filesystem into the
full disk.

## The catalog item

```yaml
record_type: catalog_item
uuid: 3f6f6d2e-9c07-4c8b-b7a4-1f2d9f6f6a01
conforms_to: udlm/0.1
tenant_uuid: 7c1e4b2a-5d3f-4e6a-9b8c-2f1a3d5e7b90
handle: cexample/game-server-workload
version: 0.1.0
name: Game-server workload (single VM, DMZ, derived DNS)
description: >-
  One VM on an isolated segment with a static address, DNS derived from declared outputs,
  and a day-0 filesystem-grow job.
constituents:
  - component_id: dmz_address
    resource_type: Network.IPAddress
    type_version: 0.6.1
    provided_by: self
    failure_effect: required
    spec_defaults:
      address: 192.0.2.20/24        # CIDR per the spec (RFC 8344 shape), not a bare address
      allocation: static

  - component_id: game_vm
    resource_type: Compute.VM
    type_version: 0.6.3
    provided_by: self
    failure_effect: required
    depends_on: [dmz_address]
    spec_defaults:
      vcpu: { count: 8 }
      memory: { size: 32GB }
      guest_os: uuid/8a2b1c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d?reference_data_type==os_image
                                            # the os_image vocabulary entry that tracks the
                                            # current server image — deferred resolution, no
                                            # runtime directory-listing discovery
      disks:
        - size: 128GB
          storage_class: cexample/host-default   # tier intent, not a filesystem path; the
                                                 # migrate-to-SSD-later becomes a spec edit
      networks:
        - name: eth0
          network_ref: cexample/dmz-segment      # host holds no address on this segment —
                                                 # only the VM's dmz_address lives there
      run_state: { desired_state: running }

  - component_id: workload_dns
    resource_type: Network.DNSZone
    type_version: 0.3.2
    provided_by: external            # DNS is fulfilled by the directory/DNS provider,
                                     # not the VM provider registering this item
    failure_effect: partial
    depends_on: [game_vm]
    bindings:
      - from_component: game_vm
        output: primary_ip
        to_field: records[0].data                # A record derives from the VM's declared
                                                 # output — it cannot drift from the real
                                                 # address the way a hand-authored record can
    spec_defaults:
      zone_name: cexample.example
      records:
        - { name: game-server, type: A, ttl: 300 }   # data arrives via the binding

  - component_id: grow_rootfs
    resource_type: Automation.Job
    type_version: 0.4.2
    provided_by: self
    failure_effect: optional
    depends_on: [game_vm]
    spec_defaults:
      definition_ref: {target_handle: cexample/automation/post-provision-setup}
      trigger: event                 # fires on the post-provision event
      max_execution_time: PT30M
```

## What the intent version improves over the playbook

| Playbook | Intent |
|---|---|
| DNS play hand-authors A+PTR with the address repeated as a literal — drift is one edit away | `workload-dns` **binds** to `game-vm`'s declared `primary_ip` output; the record cannot disagree with the realized address |
| Image discovered at runtime by fetching and grepping the release directory (respins rename the file) | the `os_image` reference resolves at realization — the vocabulary entry owns "current", the intent stays stable |
| Disk placed by literal filesystem path, with a comment noting the intended future migration | `storage_class` carries the tier intent; the migration is a one-line spec edit with version history |

Provider mechanics in the playbook — hypervisor package install, bridge/VLAN plumbing on the
host, image download, guest customization, the create command — are exactly the implementation a
VM provider owns. The host-side segment plumbing is modeled once (the host's bridge and bond
as `Hardware.NetworkInterface` records with `parent_device`), not re-created per workload.

## What the source playbook exposed as model gaps

Probing this playbook against the registry surfaced four intent elements the model cannot yet
carry — each filed for a ruling rather than silently dropped: a vCPU hot-resize ceiling
(`vcpus 8, max 16`), CPU passthrough mode, day-0 management-access bootstrap (an injected SSH
key), and thin-provisioning intent for the disk. The example above expresses everything else;
those four ride their issues.

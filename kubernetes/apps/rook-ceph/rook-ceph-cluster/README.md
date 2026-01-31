# Rook-Ceph Cluster Guidance

This document summarizes operational guidance for the Rook-Ceph cluster in this repo.
It is based on recent troubleshooting and expansion planning.

## Current Topology Assumptions

- OSDs run on worker nodes only.
- Failure domain is `host` (replicas spread across nodes).
- Replication size is 3.

## Nearfull Diagnostics (Read-Only)

Use these commands to identify nearfull OSDs and pools:

```bash
ceph osd df
ceph health detail
ceph osd tree
ceph osd dump | egrep 'nearfull|backfillfull|full'
```

Interpretation tips:

- `nearfull_ratio` is the warning threshold.
- A single nearfull OSD can flag multiple pools as nearfull.
- With mixed-size OSDs, smaller disks fill first even if total free space exists.

## Rebalancing Guidance

If the built-in balancer reports no optimization but one OSD is hotter than others:

1. Confirm balancer status:

```bash
ceph balancer status
```

2. If needed, enable balancer (safe, standard):

```bash
ceph balancer on
ceph balancer mode upmap
```

3. If balancer still shows no plan, use manual reweighting:

```bash
ceph osd reweight osd.<id> 0.95
```

Monitor and step down in small increments (0.02 to 0.05) if necessary:

```bash
ceph -s
ceph osd df
```

Alternative automatic reweight-by-utilization:

```bash
ceph osd reweight-by-utilization 110
```

Rebalancing does not create capacity.
If you are nearfull, add capacity or delete data.

## Capacity Expansion Strategy

Recommended order (safest to most risky):

1. Add larger disks to worker nodes, keep old disks temporarily, rebalance, then retire old OSDs.
2. Replace disks on workers one node at a time (swap-in-place).
3. Add OSDs to control-plane nodes (not preferred).

Reasons to avoid control-plane OSDs:

- Control-plane services are latency-sensitive.
- Lower memory (16 GiB) increases contention risk.
- Operational complexity and failure impact are higher.

Mixing sizes is supported, but large skews increase nearfull risk on smaller drives.

## Swap-In-Place (No Extra Ports)

If you cannot keep the old disk connected while adding a new one, use this workflow.
This is riskier because the cluster is degraded during each swap.
Do this one node at a time and keep the window short.

1. Confirm the cluster is stable:

```bash
ceph -s
```

2. Mark the target OSD out (start data migration while it is still online):

```bash
ceph osd out osd.<id>
```

3. Wait until recovery/backfill completes:

```bash
ceph -s
```

Look for these signals before proceeding:

- `pgs` shows only `active+clean` (no `remapped`, `recovering`, `backfilling`).
- `objects misplaced` is 0.

> [!NOTE]
> If an OSD is still `out` and you only have 3 OSDs with size=3 replication, recovery cannot finish.
> In that case, continue the swap and bring the new OSD `in` so the cluster has a third placement target.

4. Power down the node, swap the disk, and boot it back up.

```bash
sudo systemctl stop k3s
sudo systemctl disable k3s
```

5. Clear the disk to prepare it for rook-ceph

```bash
# clear disk
export DISK_ID='/dev/disk/by-id/ata-SATA_SSD_...'
sudo rm -rf /dev/ceph-*
sudo rm -rf /dev/mapper/ceph-*
sudo sgdisk --zap-all "${DISK_ID}"
sudo dd if=/dev/zero of="${DISK_ID}" bs=1M count=100 oflag=direct,dsync
sudo blkdiscard "${DISK_ID}"
sudo partprobe "${DISK_ID}"

# start k3s
sudo systemctl enable k3s
sudo systemctl start k3s
```

6. Update the Rook-Ceph HelmRelease (and Ansible vars) with the new disk by-id for that node:

`kubernetes/apps/rook-ceph/rook-ceph-cluster/app/helmrelease.yaml`

6. Verify the new OSD comes up:

```bash
ceph osd tree
ceph osd df
```

7. Confirm health returns to OK/WARN only for recovery:

```bash
ceph -s
```

> [!CAUTION]
> Do not remove a second OSD until the first swap is fully recovered!
> With size=3 and only 3 OSDs, one OSD out reduces redundancy to 2.

8. Remove old OSD from CRUSH and OSD map.

> [!CAUTION]
> Do not remove the old OSD until the swap is fully recovered!

```bash
ceph osd out osd.X
ceph osd purge osd.X --yes-i-really-mean-it
```

## Mapping OSDs to Nodes/Devices

Use these to identify which OSD is on which node/device:

```bash
ceph osd tree
ceph osd find <id>
ceph device ls-by-osd osd.<id>
```

## Notes for This Repo

- Rook-Ceph device paths are defined in:
  `kubernetes/apps/rook-ceph/rook-ceph-cluster/app/helmrelease.yaml`
- Update README if you change the storage layout or procedure.

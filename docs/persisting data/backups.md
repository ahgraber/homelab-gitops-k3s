# Backups

## Current Setup

- Persisted storage is provided via [CSI](https://github.com/democratic-csi/democratic-csi) via NFS or iSCSI shares backed by TrueNAS;
  - `Democratic-CSI` leverages native ZFS snapshots
  - TrueNAS has replication tasks to copy snapshots & preserve limited history on a separate (local) storage pool
  - TrueNAS has backup tasks to back up share directories to S3 storage (rsync/restic/kopia)
- The cluster runs [Velero](https://velero.io) for k8s-object snapshots. Application Helm charts can be annotated to preserve objects (PVs, PVCs, Pods, ...)
  - Velero backs up snapshots to offsite S3 storage.
  - It can use k8s snapshots natively, or use restic to back up volumes that are not supported by snapshots

## References

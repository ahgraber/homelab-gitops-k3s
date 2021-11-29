# Backups

## Current Setup

- Persisted storage is provided via [CSI](https://github.com/democratic-csi/democratic-csi) via NFS or iSCSI shares backed by TrueNAS;
  - `Democratic-CSI` (can) leverage native ZFS snapshots
  - TrueNAS has replication tasks to copy snapshots & preserve limited history on a separate (local) storage pool
  - TrueNAS has backup tasks to back up share directories to S3 storage (rsync/restic/kopia)
- The cluster runs [Velero](https://velero.io) for k8s-object snapshots. Application Helm charts can be annotated to preserve objects (PVs, PVCs, Pods, ...)
  - Velero backs up snapshots to offsite S3 storage.
  - It can use k8s snapshots natively, or use restic to back up volumes that are not supported by snapshots

## [Velero](https://velero.io/docs/main/)

1. Install Velero to cluster.  Optionally, install the Velero CLI to local machine.
2. If using restic to back up pod volumes, ensure that restic is enabled
3. Annotate pods with volumes to be backed up by restic: `backup.velero.io/backup-volumes=YOUR_VOLUME_NAME_1,YOUR_VOLUME_NAME_2`
4. Configure backup schedules, storage locations, snapshot locations

## References

## Future Scope

- [k8up](https://github.com/k8up-io/k8up) - waiting for [RWO PVC support](https://github.com/k8up-io/k8up/issues/319)
- [benji](https://github.com/elemental-lf/benji/tree/master/charts/benji-k8s) - best with rook/ceph

# Backups

## Current Setup

- Persisted storage is provided via [CSI](https://github.com/democratic-csi/democratic-csi) via NFS
  or iSCSI shares backed by TrueNAS;
  - `Democratic-CSI` (can) leverage native ZFS snapshots
  - TrueNAS has replication tasks to copy snapshots & preserve limited history on a separate (local)
    storage pool
  - TrueNAS has backup tasks to back up share directories to S3 storage (rsync/restic/kopia)
- The cluster runs [Velero](https://velero.io) for k8s-object snapshots. Application Helm charts can
  be annotated to preserve objects (PVs, PVCs, Pods, ...)
  - Velero backs up snapshots to offsite S3 storage.
  - It can use k8s snapshots natively, or use restic to back up volumes that are not supported by
    snapshots

## [Velero](https://velero.io/docs/main/)

1. Install Velero to cluster. Optionally, install the Velero CLI to local machine.
2. If using restic to back up pod volumes, ensure that restic is enabled
3. Annotate pods with volumes to be backed up by restic:
   `backup.velero.io/backup-volumes=YOUR_VOLUME_NAME_1,YOUR_VOLUME_NAME_2`
4. Configure backup schedules, storage locations, snapshot locations

## TrueNAS SCALE

1. Install [Restic](https://github.com/restic/restic) and [autorestic](https://github.com/cupcakearmy/autorestic)
   [using Ansible](https://github.com/ahgraber/homelab-infra/blob/main/ansible/playbooks/truenas/packages.yaml)

2. Check for updates

   ```sh
   restic self-update
   autorestic upgrade
   ```

3. [Configure `autorestic`](https://autorestic.vercel.app/config)

    ```yml
    version: 2

    locations:
      location_name:
        from: '/path/on/nas'
        to:
          - backend_name
        cron: '0 3 * * 0' # Every Sunday at 3:00
        forget: prune
        options:
          forget:
            keep-last: 5 # always keep at least 5 snapshots

    backends:
      backend_name:
        type: b2
        path: 'bucketname:/some/path'
        env:
          B2_ACCOUNT_ID: '12345'
          B2_ACCOUNT_KEY: 'qwerty'
    ```

4. Set up [crontab](https://autorestic.vercel.app/location/cron)

   ```sh
   crontab -e
   ```

   ```sh
   ### at end of file
   # This is required, as it otherwise cannot find restic as a command.
   PATH="/usr/local/bin:/usr/bin:/bin"

   # Example running every 5 minutes
   */5 * * * * autorestic -c /path/to/my/.autorestic.yml --ci cron
   ```

## References

## Future Scope

- [k8up](https://github.com/k8up-io/k8up) - waiting for
  [RWO PVC support](https://github.com/k8up-io/k8up/issues/319)
- [benji](https://github.com/elemental-lf/benji/tree/master/charts/benji-k8s) - best with rook/ceph

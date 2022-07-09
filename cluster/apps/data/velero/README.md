# [Velero](https://velero.io)

Velero is a cluster backup & restore solution. It can also leverage restic to
backup persistent volumes to S3 storage buckets.

[BackBlaze B2](https://help.backblaze.com/hc/en-us/articles/360047425453) now supports an
S3-compatible API, so we should be able to push directly.

## Bucket prefixes

Velero can mount sub-paths within the bucket as different `BackupStorageLocations` using the
`prefix` modifier. Velero assumes it has control over the location you provide so you should use a
dedicated bucket or prefix. If you provide a prefix, then the rest of the bucket is safe to use for
multiple purposes.

## Prerequisites

- [Velero CLI](https://velero.io/docs/v1.6/basic-install/#install-the-cli)
<!-- * [MinIO on BackBlaze](../minio/README.md) -->
- Bucket named `${SECRET_DOMAIN}-velero` created on BackBlaze B2 <!-- and fronted by MinIO -->

## Backup/Snapshot providers

- [Restic integration](https://velero.io/docs/v1.6/restic)
- [Velero Plugin for CSI](https://velero.io/docs/v1.6/csi/) and
  [source](https://github.com/vmware-tanzu/velero-plugin-for-csi)

## Backup

Backups can be created several ways:

1. Globally via scheduled backup (e.g. a scheduled backup)
2. Manually using schedule backup:

   ```sh
   velero backup create manually-backup-1 --from-schedule velero-daily-backup
   ```

3. Via a label selector (given a label that is present on the deployment, pv, & pvc) for the
   application

   ```sh
   velero backup create myservice \
     --include-namespaces mynamespace \
     --selector "app.kubernetes.io/instance==myservice" \
     --wait
   ```

### Restic integration

- Restic requires `opt-in` labels on pods.

  > `VOLUME_NAME` can be found by running `kubectl describe po {PODNAME} -n {NAMESPACE}` and looking
  > under `Volumes`

  ```yaml
  podAnnotations:
    backup.velero.io/backup-volumes: VOLUME_NAME
  ```

- See specifics for
  [restic integration](https://velero.io/docs/v1.6/restic/#how-backup-and-restore-work-with-restic)
  for additional pre/post-backup hooks

## Restore

In order to restore a given workload, the follow steps should work:

Given a backup exists:

1. Take required action to stop creation of new active data

   ```sh
   # Suspend flux
   flux suspend hr myservice -n mynamespace
   # Delete current resource
   kubectl delete hr myservice -n mynamespace
   # Allow the application to be redeployed and create the new resources
   sleep 600
   # Delete the unwanted new data & associated Deployment/StatefulSet/Daemonset
   kubectl delete deployment myservice -n mynamespace
   kubectl delete pvc myservice-datadir

   ### delete all resources in namespace
   # kubectl delete -n mynamespace \
   #  "$(kubectl api-resources --namespaced=true --verbs=delete -o name | tr "\n" "," | sed -e 's/,$//')" --all
   ```

2. Identify backup to use

   ```sh
   velero backup get
   ```

3. Restore the backup from restic with only the label selector

   ```sh
   velero restore create \
     --from-backup velero-daily-backup-20201120020022 \
     --include-namespaces mynamespace \
     # --selector "app.kubernetes.io/instance=myservice" \
     --wait
   ```

This should not interfere with the HelmRelease or require scaling `helm-operator` You don't need to
worry about adding labels to the HelmRelease or backing-up the helm secret object

## Backup Strategy

K8s data is persisted to TrueNAS shares - NFS and iSCSI, depending on application. _Since all
applications & services are provided via k8s, backups should be provided as a k8s service and focus
on k8s persisted volumes, and **not** be managed through the TrueNAS storage backend_

1. All PVs will be backed up to the `velero` bucket.
2. Databases will have both (a) their PVs backed up per (1), and (b) will be exported and backed up

## Future Scope

Consider [storj](https://storj.io/pricing) as BackBlaze alternative. Their
[Velero integration](https://github.com/storj/velero-plugin) is available, but not in current
development (Aug 2020)

## References

- [velero docs](https://velero.io/docs/v1.6/)
- [restic docs](https://restic.readthedocs.io/en/stable/020_installation.html#docker-container)
- <https://blah.cloud/automation/using-velero-for-k8s-backup-and-restore-of-csi-volumes/>
- <https://vraccoon.com/2020/09/velero-backup-and-restore-example/>
- [onedr0p's cluster](https://github.com/onedr0p/home-ops/tree/7f640efe61dd79d36bc51bcb72c49a8b6f1eb7a9/cluster/apps/velero)
- [billimek's cluster](https://github.com/billimek/k8s-gitops/tree/master/velero)
- [Using Velero to migrate between storage classes](https://gist.github.com/deefdragon/d58a4210622ff64088bd62a5d8a4e8cc)

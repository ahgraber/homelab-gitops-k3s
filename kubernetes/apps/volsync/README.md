# [VolSync](https://volsync.readthedocs.io/en/stable/)

VolSync is a Kubernetes operator that performs asynchronous replication of persistent volumes within/across clusters.
The replication provided by VolSync is independent of the storage system.
This allows replication to and from storage types that don't normally support remote replication.
Additionally, it can replicate across different types (and vendors) of storage.

## Example configuration

### volsync.yaml

```yaml
---
# yaml-language-server: $schema=https://kubernetes-schemas.devbu.io/replicationsource_v1alpha1.json
apiVersion: volsync.backube/v1alpha1
kind: ReplicationSource
metadata:
  name: &app APPNAME
  namespace: default
spec:
  sourcePVC: *app
  trigger:
    schedule: "0 0 * * *"
  restic:
    repository: APPNAME-restic
    retain:
      daily: 5
      weekly: 4
      monthly: 3
      yearly: 1
    pruneIntervalDays: 10
    cacheCapacity: 2Gi
    # moverSecurityContext:
    #   runAsUser: 568
    #   runAsGroup: 568
    storageClassName: ceph-block # same as source pvc
    copyMethod: Snapshot
    volumeSnapshotClassName: csi-ceph-block
```

### secret.sops.yaml.tmpl

```yaml
---
apiVersion: v1
kind: Secret
metadata:
  name: APPNAME-restic
  namespace: default
type: Opaque
stringData:
  # The repository url; add trailing folders if multiple PVCs per app (one per PVC)
  RESTIC_REPOSITORY: s3:https://${S3_ENDPOINT}/restic-APPNAME
  # The repository encryption key
  RESTIC_PASSWORD: ${DEFAULT_PWD}
  # ENV vars specific to the chosen back end
  # https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html
  AWS_ACCESS_KEY_ID: ${S3_ACCESS_KEY}
  AWS_SECRET_ACCESS_KEY: ${S3_SECRET_KEY}
```

# VolSync Template

Autorestore PVCs on rebuild.

## How it works

When deploying `fluxtomization` will substitute the variables (`postBuild.substitute`) into all resources involved in the deployment.

If the specified PVC does not exist, VolSync will attempt to restore it from the restic repo specified in the `replicationsource.yaml`

### Adding to new application

1. Add the `/templates/volsync/init` directory into the application kustomization.yaml
   (typically `../../../../templates/volsync/init` -- use `task volsync:relpath` to confirm the relative path from the application kustomization file).
2. Ensure the application `ks.yaml` is configured with `postBuild` variables
3. Wait for at least one backup (_Note: data must be present in the PVC for a backup to occur_).
4. During the first recovery, redirect to the `/templates/volsync/restore` location
   (typically `../../../../templates/volsync/restore` -- use `task volsync:relpath` to confirm the relative path from the application kustomization file).

### Adding on to an existing repo

1. Exclude `replicationdestination.yaml` or `claim.yaml` from `templates/volsync/kustomization.yaml`.  The destination will attempt to create a new PVC based on an empty/nonexistent snapshots as the backup is not yet populated.
2. Once the source has backed up, enable the `replicationdestination.yaml` and `claim.yaml` to a PVC with a **new name**.
   1. Confirm that the replication has the correct data _and_ the correct permissions
3. Update the application to use the _new PVC_
4. Update the `replicationsource` to use the _new PVC_
5. Remove the old PVC.  (Optional: do the name rotation again if you liked the first name)
6. Clean up old volsync cruft (`*-dst-dest`, `*-dst-cache`, `snapshots`)

## Configuration

### Ensure path to volsync template is in `kustomization.yaml`

```yaml
---
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ./helmrelease.yaml
  - ./sops.secrets.yaml
  # app / appname / group / apps
  - ../../../../templates/volsync
```

### Declare variables in 'fluxtomization' file (`ks.yaml`)

```yaml
  postBuild:
    substitute:
      APP: *app
      APP_UID: # set if defined in values
      APP_GID: # set if defined in values
      VOLSYNC_CAPACITY: 5Gi
      VOLSYNC_STORAGECLASS: ceph-block # default
      VOLSYNC_SNAPSHOTCLASS: csi-ceph-block # update with storageclass
      VOLSYNC_COPY_METHOD: Snapshot # default; change to "Clone" for local-path
```

### Available Variables

> Variables match [VolSync backup options](https://volsync.readthedocs.io/en/stable/usage/restic/index.html#backup-options)

For defining a replication source/destination:

- APP: \*app
- APP_UID - default: 568; for moverSecurityContext
- APP_GID - default: 568; for moverSecurityContext

- VOLSYNC_COPY_METHOD - 'Snapshot' (rook-ceph) or 'Clone' (local-path)
- VOLSYNC_CACHE_CAPACITY - default: 1Gi; must be large enough to hold non-pruned repository metadata
- VOLSYNC_SNAPSHOTCLASS - must be equivalent to source pvc (ceph-block -> csi-ceph-block; ceph-fs -> csi-ceph-fs)

For defining a PVC for restoration:

- VOLSYNC_CAPACITY - default: 5Gi
- VOLSYNC_STORAGECLASS - default: 'ceph-block'

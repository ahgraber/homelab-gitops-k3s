# VolSync Template

Autorestore PVCs on rebuild.

## How it works

When deploying `fluxtomization` will substitute the variables (`postBuild.substitute`) into all resources involved in the deployment.

If the specified PVC does not exist, VolSync will attempt to restore it from the restic repo specified in the `replicationsource.yaml`

### Adding to new application

1. Add the `/components/volsync/` directory into the application ks.yaml
   (typically `../../../components/volsync/` -- use `task volsync:relpath` to confirm the relative path from the application fluxtomization file).

2. Ensure the application `ks.yaml` is configured with `postBuild` variables

3. Wait for at least one backup (_Note: data must be present in the PVC for a backup to occur_).

   > If data exists in the pvc, and is not detected during automatic backups/snapshots, try resolving with:
   > 
   > 1) Delete the app's ReplicationSource.
   > 2) Suspend the app ks.
   > 3) Resume the app ks.

## Configuration

```yaml
# yaml-language-server: $schema=https://kubernetes-schemas.pages.dev/kustomize.toolkit.fluxcd.io/kustomization_v1.json
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: &app <appname>
  namespace: <namespace>
spec:
  ...
  dependsOn:
    - name: rook-ceph-cluster
    - name: volsync
  components:
    - ../../../components/volsync
  path: ./kubernetes/apps/<namespace>/<appname>/app
  ...
  postBuild:
    substitute:
      APP: *app
      VOLSYNC_CAPACITY: 2Gi
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

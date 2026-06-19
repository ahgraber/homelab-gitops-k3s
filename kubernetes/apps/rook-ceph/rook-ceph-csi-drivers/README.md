# rook-ceph-csi-drivers

## Purpose

Deploys the Ceph-CSI drivers (RBD + CephFS) via the upstream `ceph-csi-drivers` Helm chart.
As of **Rook v1.20** the Rook operator no longer deploys the CSI drivers itself — it only installs the `ceph-csi-operator` (controller + CRDs) as a subchart of the `rook-ceph-operator` chart.
This HelmRelease creates the `Driver` custom resources that the ceph-csi-operator reconciles into the actual node-plugin DaemonSets and controller-plugin Deployments.

Without this release, CSI provisioning and volume mounts fail.

## Configuration

Values mirror Rook's recommended defaults plus this cluster's customizations:

- `operatorConfig.namespace: rook-ceph` — must match the operator namespace.
- `operatorConfig.driverSpecDefaults.imageSet.name: rook-csi-operator-image-set-configmap`
  — reuses the image set ConfigMap published by the Rook operator chart so CSI
  images stay in lockstep with the Rook version.
- **Driver names keep the `rook-ceph.` prefix** (`rook-ceph.rbd.csi.ceph.com`, `rook-ceph.cephfs.csi.ceph.com`).
  This MUST match existing PV `spec.csi.driver` values and the StorageClass provisioner names (`csiDriverNamePrefix` in the `rook-ceph-cluster` chart).
  Changing it orphans every existing volume.
- `nodePlugin.tolerations` — node plugin DaemonSet runs on all nodes (migrated from
  the old operator `csi.pluginTolerations`).
- `controllerPlugin.tolerations` — provisioner pinned to control-plane (migrated
  from the old operator `csi.provisionerTolerations`).
- `drivers.cephfs.kernelMountOptions.ms_mode: crc` — migrated from the old operator
  `csi.cephFSKernelMountOptions: ms_mode=crc`; required because the cluster enforces
  msgr2 (`requireMsgr2: true`).
- `drivers.rbd.snapshotPolicy: volumeSnapshot` — the chart defaults the RBD driver's `snapshotPolicy` to `none`, which omits the `csi-snapshotter` sidecar from the RBD `controllerPlugin` (5/5 containers instead of 6/6).
  The old Rook-operator-managed CSI enabled the snapshotter by default, so the v1.20 split silently broke RBD `VolumeSnapshot` creation — every RBD-backed VolSync `ReplicationSource` hung at `readyToUse: false`.
  Setting this restores parity with the `cephfs` driver (which the chart already defaults to `volumeSnapshot`).
  **Gotcha:** when adding new RBD-backed apps that need snapshots, this must stay set.

### Dropped during the v1.20 migration

- `csi.enableLiveness` — no equivalent in `ceph-csi-drivers` v1.0.1.
- `cephClusterSpec.csi.readAffinity` — the CephCluster `.spec.csi` field was removed and the v1.0.1 drivers chart exposes no `readAffinity`.
  Read-locality is lost (negligible impact on a small homelab cluster).

## Dependencies

- `rook-ceph-operator` (installs the ceph-csi-operator CRDs) — enforced via Flux
  `dependsOn`.

## Source

- Chart: `ceph-csi-drivers` `1.0.1` from `https://ceph.github.io/ceph-csi-operator` (published only as an HTTP Helm repo; no OCI registry).
  Version tracks the `ceph-csi-operator` subchart bundled by Rook v1.20.0.

## Links

- [Rook v1.20 upgrade guide](https://rook.github.io/docs/rook/v1.20/Upgrade/rook-upgrade/)
- [Ceph-CSI drivers chart docs](https://rook.github.io/docs/rook/v1.20/Helm-Charts/csi-drivers-chart/)
- [ceph-csi-operator drivers chart config](https://github.com/ceph/ceph-csi-operator/blob/main/docs/helm-charts/drivers-chart.md)

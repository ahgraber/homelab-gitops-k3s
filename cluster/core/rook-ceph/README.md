# Rook-ceph

_Rook_ is an open source cloud-native storage orchestrator, providing the platform, framework, and support for a diverse set of storage solutions to natively integrate with cloud-native environments.

_Ceph_ is a highly scalable distributed storage solution, delivering object, block,
and file storage in one unified system.

## Requirements

1. Nodes with `amd64`/`arm64` architecture
2. Nodes with dedicated local storage
   - Storage can be allocated directly via cluster definition (`storage.config.node`)
     or provided via local pvc using `local-path` storageClass or `spec.local.path` natively in pvc definition
   - If provisioning local disks, the disks must be raw/unformatted ([ref](https://rook.io/docs/rook/v1.9/pre-reqs.html))

## Resources

[Quickstart](https://rook.io/docs/rook/latest/Getting-Started/quickstart/)
[Deployment examples](https://github.com/rook/rook/tree/master/deploy/examples)

## Teardown and Cleanup

[Documentation](https://rook.io/docs/rook/v1.0/ceph-teardown.html)

```sh
kubectl patch cephcluster rook-ceph -n rook-ceph --type merge -p '{"spec":{"cleanupPolicy":{"confirmation":"yes-really-destroy-data"}}}'
kubectl delete hr rook-ceph-cluster -n rook-ceph
kubectl delete cephcluster rook-ceph -n rook-ceph
```

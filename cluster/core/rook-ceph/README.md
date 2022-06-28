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

> Order of operations is critical!  See [documentation](https://rook.io/docs/rook/v1.0/ceph-teardown.html)

1. Pause Flux reconcilation or remove kustomization/s (at least the rook-ceph cluster) from git repo
2. Delete the cluster helm release (and associated configmaps) or `kubectl delete -k ./cluster/core/rook-ceph/cluster`.
   **DO NOT REMOVE THE ORCHESTRATOR**
3. Delete the cephcluster custom resource (if it still exists)
4. Check crds for remaining objects

```sh
kubectl patch cephcluster rook-ceph -n rook-ceph --type merge -p '{"spec":{"cleanupPolicy":{"confirmation":"yes-really-destroy-data"}}}'
kubectl delete hr rook-ceph-cluster -n rook-ceph
kubectl delete cephcluster rook-ceph -n rook-ceph
# clean up CRDS
for CRD in $(kubectl get crd -A -o name | grep ceph.rook.io); do kubectl delete "$CRD"; done;
# NOTE: may have to edit/patch custom resources to delete them prior to force-removing finalzers for crds
for CRD in $(kubectl get crd -A -o name | grep ceph.rook.io); do
  kubectl patch "$CRD" --type merge -p '{"metadata":{"finalizers": []}}'
done

for RES in $(kubectl get configmap,secret -n rook-ceph -o name); do kubectl delete "$RES" -n rook-ceph; done;
for RES in $(kubectl get configmap,secret -n rook-ceph -o name); do
  kubectl patch "$RES" -n rook-ceph --type merge -p '{"metadata":{"finalizers": []}}'
done
kubectl delete ns rook-ceph
kubectl patch ns rook-ceph --type merge -p '{"metadata":{"finalizers": []}}'
```

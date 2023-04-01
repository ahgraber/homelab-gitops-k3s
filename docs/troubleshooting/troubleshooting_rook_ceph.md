# Troubleshooting Rook-Ceph

## Teardown and Cleanup

> Order of operations is critical!  See [documentation](https://rook.io/docs/rook/v1.0/ceph-teardown.html)

1. Suspend Flux reconciliation or remove kustomization/s (at least the rook-ceph cluster) from git repo
2. Delete the cluster helm release (and associated configmaps) or `kubectl delete -k ./cluster/core/rook-ceph/cluster`.
   **DO NOT REMOVE THE ORCHESTRATOR**
3. Delete the cephcluster custom resource (if it still exists)
4. Check crds for remaining objects

```sh
# get hanging resources
 kubectl api-resources --verbs=list --namespaced -o name \
  | xargs -n 1 kubectl get --show-kind --ignore-not-found -n rook-ceph
flux suspend kustomization rook-ceph
kubectl patch cephcluster rook-ceph -n rook-ceph --type merge -p '{"spec":{"cleanupPolicy":{"confirmation":"yes-really-destroy-data"}}}'
kubectl delete hr rook-ceph-cluster -n rook-ceph
kubectl delete cephcluster rook-ceph -n rook-ceph
kubectl patch cephcluster rook-ceph -n rook-ceph --type merge -p '{"metadata":{"finalizers": []}}'
for RES in $(kubectl get configmap,secret -n rook-ceph -o name); do
  kubectl patch "$RES" -n rook-ceph --type merge -p '{"metadata":{"finalizers": []}}'
  kubectl delete "$RES" -n rook-ceph
done
for CRD in $(kubectl get crd -A -o name | grep ceph.rook.io); do
  kubectl patch "$CRD" --type merge -p '{"metadata":{"finalizers": []}}'
  kubectl delete "$CRD"
done;
kubectl patch ns rook-ceph --type merge -p '{"metadata":{"finalizers": []}}'
kubectl delete ns rook-ceph

### RUN ROOK-CEPH-CLEANUP ANSIBLE SCRIPT
```

## Remove orphan rbd images

1. With `kubectl`, list all currently-in-use PVs by storage class

   ```sh
   # with add'l info
   k get pv -o json \
     | jq '.items[]
     | select(.spec.storageClassName == "ceph-block-retain")
     | {name: .metadata.name, usedby: .spec.claimRef.name, imageName: .spec.csi.volumeAttributes.imageName}'

   # just the rook-ceph imageNames
   k get pv -o json \
     | jq '.items[]
     | select(.spec.storageClassName == "ceph-block-retain")
     | .spec.csi.volumeAttributes.imageName'
   ```

2. From `ceph toolbox` pod, list of existing ceph RBD images by storage class

   ```sh
   rbd ls -p ceph-blockpool-retain
   ```

3. In `ceph toolbox` pod, create arrays

   ```sh
   # from kubectl command, copy list of imageNames
   pvs=(< copy outputs from step 1 >)
   # pvs=("csi-vol-9918487c-718e-11ed-af1c-d608edb9ade0" \
   # "csi-vol-7f05fdba-8847-11ed-af1c-d608edb9ade0" \
   # "csi-vol-30448e88-74fd-11ed-af1c-d608edb9ade0" \
   # )
   echo "${pvs[0]}"

   # create array from rbd command
   imgs=($(rbd ls -p ceph-blockpool-retain))
   echo "${pvs[0]}"
   ```

4. In `ceph toolbox` pod, compare arrays and remove trash

   ```sh
   toremove=($(echo ${imgs[@]} ${pvs[@]} | tr ' ' '\n' | sort | uniq -u))
   echo "${toremove[@]}"
   for img in "${toremove[@]}"; do
     echo "Removing $img"
     rbd rm "$img" -p ceph-blockpool-retain
   done
   ```

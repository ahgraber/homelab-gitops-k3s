# Troubleshooting Rook-Ceph

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

   # create array from rbd comand
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

`

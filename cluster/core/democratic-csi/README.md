# Democratic-CSI

`democratic-csi` implements the `csi` (container storage interface) spec providing storage for various container orchestration systems (ie: Kubernetes).

The current focus is providing storage via iscsi/nfs from zfs-based storage systems, predominantly `FreeNAS / TrueNAS` and `ZoL` on `Ubuntu`.

The current drivers implement the depth and breadth of the `csi` spec, providing access to resizing, snapshots, clones, etc functionality.

## Prerequisites

### Node Prep

- `nfs`: Ensure that `nfs-common` has been installed on nodes
- `iscsi`:
  - Ensure that `open-iscsi lsscsi sg3-utils multipath-tools scsitools` are installed on nodes

    ```sh
    sudo apt install open-iscsi lsscsi sg3-utils multipath-tools scsitools
    ```

  - Enable multipathing:

    ```sh
    # Enable multipathing
    sudo tee /etc/multipath.conf <<- 'EOF'
    defaults {
        user_friendly_names yes
        find_multipaths yes
    }
    EOF

    sudo systemctl enable multipath-tools.service
    sudo service multipath-tools restart
    ```

  - Check that services are up and running

    ```sh
    # Ensure that open-iscsi and multipath-tools are enabled and running
    sudo systemctl status multipath-tools
    sudo systemctl enable open-iscsi.service
    sudo service open-iscsi start
    sudo systemctl status open-iscsi
    ```

### [TrueNas / Server Prep](https://github.com/democratic-csi/democratic-csi#server-prep)

- Create user `csi`
  - set `bash` shell
  - provide `id_rsa` public key for passwordless login
  - ensure part of `www-data` group
  - note `uid` and `gid` of user
- Provide passwordless sudo priviledges:
  _Normally, you'd do this:_

  ```sh
  nano /etc/sudoers
  # ensure the following line is present
  csi ALL=(ALL) NOPASSWD:ALL
  ```

  _Note: But this **WILL** get reset by truenas_
  _instead, use truenas `cli`:_

  ```sh
  # at the command prompt
  sudo cli
  # after you enter the truenas cli and are at that prompt
  account user query id,username,uid,sudo_nopasswd
  # find the `id` of the user you want to update (note, this is distinct from the `uid`)
  account user update id= < id > sudo_nopasswd=true
  # exit cli by hitting ctrl-d
  # confirm sudoers file is appropriate
  cat /usr/local/etc/sudoers
  ```

- Generate API key `csi` and save to text file for k8s secret
- Enable NFS share
  - _Note: May have to set "NFSv3 ownership model for NFSv4"_
- Set nfs parent dataset permissions for RWX for `csi` user and appropriate group
- May have to reload nfs service: `sudo systemctl restart nfs-ganesha`

## Configuration

`democratic-csi` uses config secrets to hold sensitive information and those configmaps are passed into the helm values.

- See [generic nfs configuration](https://github.com/democratic-csi/charts/blob/master/stable/democratic-csi/examples/nfs-client.yaml) using [nfs driver](https://github.com/democratic-csi/democratic-csi/blob/master/examples/nfs-client.yaml)
- See [truenas nfs configuration](https://github.com/democratic-csi/charts/blob/master/stable/democratic-csi/examples/freenas-nfs.yaml) using [freenas driver](https://github.com/democratic-csi/democratic-csi/blob/master/examples/freenas-nfs.yaml)
- See [truenas iscsi configuration](https://github.com/democratic-csi/charts/blob/master/stable/democratic-csi/examples/freenas-iscsi.yaml) using [iscsi driver](https://github.com/democratic-csi/democratic-csi/blob/master/examples/freenas-iscsi.yaml)

### iSCSI

iSCSI PVs will 'retain' on deletion of PVC.  Will have to manually delete from kubernetes cluster _and_ delete both `targets` and `extents` from truenas iscsi share.

### NFS

NFS PVs will 'delete' on deletion of PVC.

## Debug

* If get `message: '{"code":32,"stdout":"","stderr":"mount.nfs: access denied by server while mounting 10.2.1.1:/mnt/ssdpool/csi/nfs/v/pvc-...}`, restart NFS service on NAS

* iSCSI volumes require deleting the target and extent on the server; new PVCs/PVs on k8s side will reuse the same extent on the NAS.

* [cleanup old/broken snapshots](https://serverfault.com/questions/340837/how-to-delete-all-but-last-n-zfs-snapshots) with:

  ```sh
  # remove empty snapshots
  zfs list -t snapshot | awk ' $2 == "0B" { print $1 }' | xargs -n1 echo
  # zfs list -t snapshot | awk ' $2 == "0B" ' | xargs -n1 zfs destroy

  zfs list -t snapshot -H -o name | grep "<SEARCH STRING TO MATCH>" | xargs -n1 echo
  # zfs list -t snapshot -H -o name | grep "201509[0-9].*" | xargs -n1 zfs destroy
  ```

# Rook-Ceph

- [Rook-Ceph](#rook-ceph)
  - [Intro](#intro)
  - [Requirements](#requirements)
  - [Updating](#updating)
  - [Teardown and Cleanup](#teardown-and-cleanup)
  - [Troubleshooting](#troubleshooting)
    - [Dashboard not accessible thru ingress](#dashboard-not-accessible-thru-ingress)
    - [Integrate with Prometheus/Alertmanager](#integrate-with-prometheusalertmanager)
    - [Crash](#crash)
    - [View OSD pods](#view-osd-pods)
    - [Too many PGs per OSD](#too-many-pgs-per-osd)
    - [Ceph Mon Low Space warning](#ceph-mon-low-space-warning)
      - [Identify what is taking up all of the space](#identify-what-is-taking-up-all-of-the-space)
      - [Clean up logs](#clean-up-logs)
      - [Clean up unused images](#clean-up-unused-images)
  - [Remove orphan rbd images](#remove-orphan-rbd-images)

## Intro

[Quickstart](https://rook.io/docs/rook/latest/Getting-Started/quickstart/)
[Deployment examples](https://github.com/rook/rook/tree/master/deploy/examples)
[eli5](https://koor.tech/blog/2022/kubernetes-deserves-more-than-ephemeral-data-persist-it-with-rook/)

_Rook_ is an open source cloud-native storage orchestrator, providing the platform, framework, and support
for running ceph on kubernetes.

_Ceph_ is a highly scalable distributed storage solution, providing object, block,and file storage.

## Requirements

1. Nodes with `amd64`/`arm64` architecture
2. Nodes with dedicated local storage
   - Storage can be allocated directly via cluster definition (`storage.config.node`)
     or provided via local pvc using `local-path` storageClass or `spec.local.path` natively in pvc definition
   - If provisioning local disks, the disks must be raw/unformatted ([ref](https://rook.io/docs/rook/v1.9/pre-reqs.html))

## Updating

[Health verification](https://rook.github.io/docs/rook/v1.10/Upgrade/health-verification/)
[Rook upgrade](https://rook.github.io/docs/rook/v1.10/Upgrade/rook-upgrade/)
[Ceph upgrade](https://rook.github.io/docs/rook/v1.10/Upgrade/ceph-upgrade/)

## Teardown and Cleanup

> Order of operations is critical!  See [documentation](https://rook.io/docs/rook/v1.11/Getting-Started/ceph-teardown)

Run `task rook:decommission`

## Troubleshooting

<!-- ### Ceph reports no orchestrator configured

> run the following commands against the ceph-toolbox pod
>
> access with
>
>  ```sh
> kubectl -n rook-ceph exec -it \
>   $(kubectl -n rook-ceph get pod -l "app=rook-ceph-tools" -o jsonpath='{.items[0].metadata.name}') -- bash
> ```

```sh
ceph mgr module enable rook && ceph orch set backend rook && ceph orch status
``` -->

### Dashboard not accessible thru ingress

> ! If this happens, doublecheck the `cephClusterSpec.dashboard` section of the helm values
>
> To fix manually, run the following commands against the ceph-toolbox pod:

```sh
ceph mgr module disable dashboard
ceph config set mgr mgr/dashboard/ssl false
ceph mgr module enable dashboard
```

### Integrate with Prometheus/Alertmanager

> run the following commands against the ceph-toolbox pod

```sh
ceph
dashboard set-alertmanager-api-host 'http://kps-alertmanager.monitoring.svc.cluster.local:9093'
dashboard set-alertmanager-api-ssl-verify False
dashboard set-prometheus-api-host 'http://kps-prometheus.monitoring.svc.cluster.local:9090'
dashboard set-prometheus-api-ssl-verify False
```

### Crash

> run the following commands against the ceph-toolbox pod
> hint `task rook:toolbox`

```sh
ceph health detail
# get new crashes
ceph crash ls-new
# get crash info
ceph crash info <crashid>
# archive crash so it doesn't keep triggering warnings or show in 'ls-new'
ceph crash archive-all
```

[docs](https://docs.ceph.com/en/quincy/mgr/crash/)

### View OSD pods

> run the following commands against the ceph-toolbox pod

List current OSD pools:

```sh
ceph osd tree
ceph osd pool ls
```

Get current autoscale status (and coincidentally pg_num):

```sh
ceph osd pool autoscale-status
```

List pools

```sh
ceph osd lspools
```

List current placement groups:

```sh
ceph pg dump # list
ceph pg stat # status
```

```sh
# Get OSD Pods
# This uses the example/default cluster name "rook"
OSD_PODS=$(kubectl get pods --all-namespaces -l \
  app=rook-ceph-osd,rook_cluster=rook-ceph -o jsonpath='{.items[*].metadata.name}')

# Find node and drive associations from OSD pods
for pod in $(echo ${OSD_PODS})
do
 echo "Pod:  ${pod}"
 echo "Node: $(kubectl -n rook-ceph get pod ${pod} -o jsonpath='{.spec.nodeName}')"
 kubectl -n rook-ceph exec ${pod} -- sh -c '\
  for i in /var/lib/ceph/osd/ceph-*; do
    [ -f ${i}/ready ] || continue
    echo -ne "-$(basename ${i}) "
    echo $(lsblk -n -o NAME,SIZE ${i}/block 2> /dev/null || \
    findmnt -n -v -o SOURCE,SIZE -T ${i}) $(cat ${i}/type)
  done | sort -V
  echo'
done
```

### Too many PGs per OSD

> run the following commands against the ceph-toolbox pod

Show current PGs/OSD:

<!-- markdownlint-disable -->
```sh
ceph pg dump | awk '
BEGIN { IGNORECASE = 1 }
 /^PG_STAT/ { col=1; while($col!="UP") {col++}; col++ }
 /^[0-9a-f]+\.[0-9a-f]+/ { match($0,/^[0-9a-f]+/); pool=substr($0, RSTART, RLENGTH); poollist[pool]=0;
 up=$col; i=0; RSTART=0; RLENGTH=0; delete osds; while(match(up,/[0-9]+/)>0) { osds[++i]=substr(up,RSTART,RLENGTH); up = substr(up, RSTART+RLENGTH) }
 for(i in osds) {array[osds[i],pool]++; osdlist[osds[i]];}
}
END {
 printf("\n");
 printf("pool :\t"); for (i in poollist) printf("%s\t",i); printf("| SUM \n");
 for (i in poollist) printf("--------"); printf("----------------\n");
 for (i in osdlist) { printf("osd.%i\t", i); sum=0;
   for (j in poollist) { printf("%i\t", array[i,j]); sum+=array[i,j]; sumpool[j]+=array[i,j] }; printf("| %i\n",sum) }
 for (i in poollist) printf("--------"); printf("----------------\n");
 printf("SUM :\t"); for (i in poollist) printf("%s\t",sumpool[i]); printf("|\n");
}'
```
<!-- markdownlint-enable -->

> The general rules for deciding how many PGs your pool(s) should contain is:
>
> - Fewer than 5 OSDs set pg_num to 128
> - Between 5 and 10 OSDs set pg_num to 512
> - Between 10 and 50 OSDs set pg_num to 1024
>
> ```sh
> ceph osd pool set <name> pg_num 128
> ```

<!-- For more specifics, we can specify pg_num per osd pool.
Based on [PGcalc](https://old.ceph.com/pgcalc/), assuming a 3-drive cluster with 3 replicas,
we want 4, 8, or 16 pgs per osd pool, depending on anticipated utilization
(larger # for pools with anticipated larger data requirements).
This may take a few runs for rook-ceph to sort out the changes on the back end

```sh
# for each pool name -- this will depend on ceph cluster deployment
ceph osd pool set .mgr pg_num 4
ceph osd pool set .rgw.root pg_num 32
ceph osd pool set ceph-blockpool pg_num 32
ceph osd pool set ceph-filesystem-metadata pg_num 16
ceph osd pool set ceph-filesystem-data0 pg_num 16
ceph osd pool set ceph-objectstore.rgw.buckets.index pg_num 16
ceph osd pool set ceph-objectstore.rgw.buckets.non-ec pg_num 16
ceph osd pool set ceph-objectstore.rgw.buckets.data pg_num 16
ceph osd pool set ceph-objectstore.rgw.control pg_num 16
ceph osd pool set ceph-objectstore.rgw.log pg_num 16
ceph osd pool set ceph-objectstore.rgw.meta pg_num 16
``` -->

[docs - configuring pools](https://rook.io/docs/rook/v1.9/Storage-Configuration/Advanced/ceph-configuration/#configuring-pools)
[docs - monitoring osds & pgs](https://docs.ceph.com/en/latest/rados/operations/monitoring-osd-pg/)
[docs - placement groups](https://docs.ceph.com/en/latest/rados/operations/placement-groups/#a-preselection-of-pg-num)
[stackoverflow](https://stackoverflow.com/questions/39589696/ceph-too-many-pgs-per-osd-all-you-need-to-know)
[cephnotes](http://cephnotes.ksperis.com/blog/2015/02/23/get-the-number-of-placement-groups-per-osd)
[pgcalc](https://old.ceph.com/pgcalc/)

### Ceph Mon Low Space warning

#### Identify what is taking up all of the space

```sh
# check disk space
df -h
# identify large directories
sudo du -hsx /* | sort -rh | head -n 10
# identify what is taking space in directory /var
sudo du -a /var | sort -n -r | head -n 20
```

#### Clean up logs

```sh
# if /var/lib/journal is the problem, rotate and vacuum
sudo systemctl kill --kill-who=main --signal=SIGUSR2 systemd-journald.service
sudo journalctl --vacuum-size=50M
```

#### Clean up unused images

```sh
ssh ...
sudo k3s crictl rmi --prune
```

## Remove orphan rbd images

1. With `kubectl`, list all currently-in-use PVs by storage class

   ```sh
   # with add'l info
   k get pv -o json \
     | jq '.items[]
     | select(.spec.storageClassName == "ceph-block")
     | {name: .metadata.name, usedby: .spec.claimRef.name, imageName: .spec.csi.volumeAttributes.imageName}'

   # just the rook-ceph imageNames
   k get pv -o json \
     | jq '.items[]
     | select(.spec.storageClassName == "ceph-block")
     | .spec.csi.volumeAttributes.imageName'
   ```

2. From `ceph toolbox` pod, list of existing ceph RBD images by storage class

   ```sh
   rbd ls -p ceph-blockpool
   ```

3. In `ceph toolbox` pod, create arrays

   ```sh
   # from kubectl command, copy list of imageNames
   pvs=(<copy outputs from step 1>)
   # pvs=("csi-vol-9918487c-718e-11ed-af1c-d608edb9ade0" \
   # "csi-vol-7f05fdba-8847-11ed-af1c-d608edb9ade0" \
   # "csi-vol-30448e88-74fd-11ed-af1c-d608edb9ade0" \
   # )
   echo "${pvs[0]}"

   # create array from rbd command
   imgs=($(rbd ls -p ceph-blockpool))
   echo "${imgs[0]}"
   ```

4. In `ceph toolbox` pod, compare arrays and remove trash

   ```sh
   toremove=($(echo ${imgs[@]} ${pvs[@]} | tr ' ' '\n' | sort | uniq -u))
   echo "${toremove[@]}"
   for img in "${toremove[@]}"; do
     echo "Removing $img"
     rbd rm "$img" -p ceph-blockpool
   done
   ```

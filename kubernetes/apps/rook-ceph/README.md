# Rook-ceph

_Rook_ is an open source cloud-native storage orchestrator, providing the platform, framework, and support
for running ceph on kubernetes.

_Ceph_ is a highly scalable distributed storage solution, providing object, block,and file storage.

## Requirements

1. Nodes with `amd64`/`arm64` architecture
2. Nodes with dedicated local storage
   - Storage can be allocated directly via cluster definition (`storage.config.node`)
     or provided via local pvc using `local-path` storageClass or `spec.local.path` natively in pvc definition
   - If provisioning local disks, the disks must be raw/unformatted ([ref](https://rook.io/docs/rook/v1.9/pre-reqs.html))

## Resources

[Quickstart](https://rook.io/docs/rook/latest/Getting-Started/quickstart/)
[Deployment examples](https://github.com/rook/rook/tree/master/deploy/examples)
[eli5](https://koor.tech/blog/2022/kubernetes-deserves-more-than-ephemeral-data-persist-it-with-rook/)

## Updating

[Health verification](https://rook.github.io/docs/rook/v1.10/Upgrade/health-verification/)
[Rook upgrade](https://rook.github.io/docs/rook/v1.10/Upgrade/rook-upgrade/)
[Ceph upgrade](https://rook.github.io/docs/rook/v1.10/Upgrade/ceph-upgrade/)

### Rook version update

<!-- markdownlint-disable -->
```sh
ROOK_CLUSTER_NAMESPACE="rook-ceph"

# watch update occur
watch --exec kubectl -n "${ROOK_CLUSTER_NAMESPACE}" get deployments \
  -l "rook_cluster=${ROOK_CLUSTER_NAMESPACE}" \
  -o jsonpath='{range .items[*]}{.metadata.name}{"  \treq/upd/avl: "}{.spec.replicas}{"/"}{.status.updatedReplicas}{"/"}{.status.readyReplicas}{"  \trook-version="}{.metadata.labels.rook-version}{"\n"}{end}'

# check only a single version is left
kubectl -n "${ROOK_CLUSTER_NAMESPACE}" get deployment \
  -l "rook_cluster=${ROOK_CLUSTER_NAMESPACE}" \
  -o jsonpath='{range .items[*]}{"rook-version="}{.metadata.labels.rook-version}{"\n"}{end}' | sort | uniq
```
<!-- markdownlint-enable -->

### Ceph version update

<!-- markdownlint-disable -->
```sh
ROOK_CLUSTER_NAMESPACE="rook-ceph"

# watch update occur
watch --exec kubectl -n "${ROOK_CLUSTER_NAMESPACE}" get deployments \
  -l "rook_cluster=${ROOK_CLUSTER_NAMESPACE}" \
  -o jsonpath='{range .items[*]}{.metadata.name}{"  \treq/upd/avl: "}{.spec.replicas}{"/"}{.status.updatedReplicas}{"/"}{.status.readyReplicas}{"  \tceph-version="}{.metadata.labels.ceph-version}{"\n"}{end}'

# check only a single version is left
kubectl -n "${ROOK_CLUSTER_NAMESPACE}" get deployment \
  -l "rook_cluster=${ROOK_CLUSTER_NAMESPACE}" \
  -o jsonpath='{range .items[*]}{"ceph-version="}{.metadata.labels.ceph-version}{"\n"}{end}' | sort | uniq
```
<!-- markdownlint-enable -->

## Troubleshooting

### Dashboard not accessible thru ingress

> run the following commands against the ceph-toolbox pod

```sh
ceph mgr module disable dashboard
ceph config set mgr mgr/dashboard/ssl false
ceph mgr module enable dashboard
```

### Integrate with Prometheus/Alertmanager

> run the following commands against the ceph-toolbox pod

```sh
ceph
dashboard set-alertmanager-api-host 'http://kps-alertmanager.monitoring.svc:9093'
dashboard set-alertmanager-api-ssl-verify False
dashboard set-prometheus-api-host 'http://kps-prometheus.monitoring.svc:9090'
dashboard set-prometheus-api-ssl-verify False
```

### Crash

> run the following commands against the ceph-toolbox pod

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

## Teardown and Cleanup

> Order of operations is critical!  See [documentation](https://rook.io/docs/rook/v1.9/ceph-teardown.html)

1. Suspend Flux reconciliation or remove kustomization/s (at least the rook-ceph cluster) from git repo
2. Delete the cluster helm release (and associated configmaps) or `kubectl delete -k ./kubernetes/apps/rook-ceph/rook-ceph/cluster/`.
   **DO NOT REMOVE THE ORCHESTRATOR**
3. Delete the cephcluster custom resource (if it still exists)
4. Check crds for remaining objects

```sh
# get hanging resources
#  kubectl get all -o name \
#   | xargs -n 1 kubectl get --show-kind --ignore-not-found -n rook-ceph
flux suspend kustomization apps-rook-ceph-cluster
flux suspend kustomization apps-rook-ceph-operator
kubectl patch cephcluster rook-ceph -n rook-ceph --type merge -p '{"spec":{"cleanupPolicy":{"confirmation":"yes-really-destroy-data"}}}'
kubectl patch cephcluster rook-ceph -n rook-ceph --type merge -p '{"metadata":{"finalizers": []}}'
kubectl delete cephcluster rook-ceph -n rook-ceph
kubectl delete hr rook-ceph-cluster -n rook-ceph
for RES in $(kubectl get configmap,secret -n rook-ceph -o name); do
  kubectl patch "$RES" -n rook-ceph --type merge -p '{"metadata":{"finalizers": []}}'
  kubectl delete "$RES" -n rook-ceph
done
for CRD in $(kubectl get crd -A -o name | grep ceph.rook.io); do
  kubectl patch "$CRD" --type merge -p '{"metadata":{"finalizers": []}}'
  kubectl delete "$CRD"
done;
flux delete kustomization apps-rook-ceph-cluster -s
kubectl delete hr rook-ceph-operator -n rook-ceph
flux delete kustomization apps-rook-ceph-operator -s
kubectl patch ns rook-ceph --type merge -p '{"spec":{"finalizers": []}}'
kubectl delete ns rook-ceph

echo "!!! Don't forget to run rook-ceph cleanup ansible script !!!"
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
   rbd ls -p ceph-blockpool
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

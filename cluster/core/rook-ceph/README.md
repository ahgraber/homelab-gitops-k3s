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

## Troubleshooting

### Integrate with Prometheus/Alertmanager

> run the following commands against the ceph-toolbox pod

```sh
ceph
dashboard set-alertmanager-api-host 'http://alertmanager-operated.monitoring.svc:9093'
dashboard set-alertmanager-api-ssl-verify False
dashboard set-prometheus-api-host 'http://prometheus-operated.monitoring.svc:9090'
dashboard set-prometheus-api-ssl-verify False
```

### Too many PGs per OSD

[stackoverflow](https://stackoverflow.com/questions/39589696/ceph-too-many-pgs-per-osd-all-you-need-to-know)
[cephnotes](http://cephnotes.ksperis.com/blog/2015/02/23/get-the-number-of-placement-groups-per-osd)
[pgcalc](https://old.ceph.com/pgcalc/)

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

List current OSD pools:

```sh
ceph osd pool ls
```

Based on PGcalc, and 3-drive cluster with 3 replicas, we basically want 4, 8, or 16 pgs per osd pool,
depending on anticipated use (larger # for pools with anticipated larger data requirements).
This may take a few runs for rook-ceph to sort out the changes on the back end

```sh
# for each pool name -- this will depend on ceph cluster deployment
ceph osd pool set .mgr pg_num 4
ceph osd pool set .rgw.root pg_num 32
ceph osd pool set ceph-blockpool pg_num 16
ceph osd pool set ceph-blockpool-retain pg_num 16
ceph osd pool set ceph-filesystem-metadata pg_num 16
ceph osd pool set ceph-filesystem-data0 pg_num 16
ceph osd pool set ceph-objectstore.rgw.buckets.index pg_num 16
ceph osd pool set ceph-objectstore.rgw.buckets.non-ec pg_num 16
ceph osd pool set ceph-objectstore.rgw.buckets.data pg_num 16
ceph osd pool set ceph-objectstore.rgw.control pg_num 16
ceph osd pool set ceph-objectstore.rgw.log pg_num 16
ceph osd pool set ceph-objectstore.rgw.meta pg_num 16
```

## Teardown and Cleanup

> Order of operations is critical!  See [documentation](https://rook.io/docs/rook/v1.0/ceph-teardown.html)

1. Suspend Flux reconcilation or remove kustomization/s (at least the rook-ceph cluster) from git repo
2. Delete the cluster helm release (and associated configmaps) or `kubectl delete -k ./cluster/core/rook-ceph/cluster`.
   **DO NOT REMOVE THE ORCHESTRATOR**
3. Delete the cephcluster custom resource (if it still exists)
4. Check crds for remaining objects

```sh
flux suspend kustomization core
kubectl patch cephcluster rook-ceph -n rook-ceph --type merge -p '{"spec":{"cleanupPolicy":{"confirmation":"yes-really-destroy-data"}}}'
kubectl delete hr rook-ceph-cluster -n rook-ceph
kubectl delete cephcluster rook-ceph -n rook-ceph
kubectl patch cephcluster rook-ceph -n rook-ceph --type merge -p '{"metadata":{"finalizers": []}}'
# clean up CRDS
for CRD in $(kubectl get crd -A -o name | grep ceph.rook.io); do
  kubectl delete "$CRD"
  kubectl patch "$CRD" --type merge -p '{"metadata":{"finalizers": []}}'
done;

for RES in $(kubectl get configmap,secret -n rook-ceph -o name); do
  kubectl delete "$RES" -n rook-ceph
  kubectl patch "$RES" -n rook-ceph --type merge -p '{"metadata":{"finalizers": []}}'
done

kubectl delete ns rook-ceph
kubectl patch ns rook-ceph --type merge -p '{"metadata":{"finalizers": []}}'

### RUN ROOK-CEPH-CLEANUP ANSIBLE SCRIPT
```

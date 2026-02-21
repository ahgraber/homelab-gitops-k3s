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
    - [BlueStore slow operations](#bluestore-slow-operations)
      - [Diagnose the issue](#diagnose-the-issue)
      - [Force compaction](#force-compaction)
    - [Ceph Mon Low Space warning](#ceph-mon-low-space-warning)
      - [Identify what is taking up all of the space](#identify-what-is-taking-up-all-of-the-space)
      - [Clean up logs](#clean-up-logs)
      - [Clean up unused images](#clean-up-unused-images)
      - [Restart pods](#restart-pods)
  - [Remove orphan rbd images](#remove-orphan-rbd-images)
    - [Common usage](#common-usage)

## Intro

[Quickstart](https://rook.io/docs/rook/latest/Getting-Started/quickstart/) [Deployment examples](https://github.com/rook/rook/tree/master/deploy/examples) [eli5](https://koor.tech/blog/2022/kubernetes-deserves-more-than-ephemeral-data-persist-it-with-rook/)

_Rook_ is an open source cloud-native storage orchestrator, providing the platform, framework, and support
for running ceph on kubernetes.

_Ceph_ is a highly scalable distributed storage solution, providing object, block,and file storage.

## Requirements

1. Nodes with `amd64`/`arm64` architecture
2. Nodes with dedicated local storage
   - Storage can be allocated directly via cluster definition (`storage.config.node`)
     or provided via local pvc using `openebs-hostpath` storageClass or `spec.local.path` natively in pvc definition
   - If provisioning local disks, the disks must be raw/unformatted

## Updating

- [Health verification](https://rook.github.io/docs/rook/v1.19/Upgrade/health-verification/)
- [Rook upgrade](https://rook.github.io/docs/rook/v1.19/Upgrade/rook-upgrade/)
- [Ceph upgrade](https://rook.github.io/docs/rook/v1.19/Upgrade/ceph-upgrade/)

## Teardown and Cleanup

> Order of operations is critical! See [documentation](https://rook.io/docs/rook/v1.19/Getting-Started/ceph-teardown)

Run `task rook:decommission`

## Troubleshooting

<!-- ### Ceph reports no orchestrator configured

> run the following commands against the ceph-toolbox pod
>
> access with
>
> ```sh
> kubectl -n rook-ceph exec -it \
> $(kubectl -n rook-ceph get pod -l "app=rook-ceph-tools" -o jsonpath='{.items[0].metadata.name}') -- bash
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
dashboard set-alertmanager-api-host 'http://kube-prometheus-stack-alertmanager.monitoring.svc.cluster.local:9093'
dashboard set-alertmanager-api-ssl-verify False
dashboard set-prometheus-api-host 'http://kube-prometheus-stack-prometheus.monitoring.svc.cluster.local:9090'
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

```sh
ceph pg dump | awk '
BEGIN { IGNORECASE = 1 }
 /^PG_STAT/ { col=1; while($col!="UP") {col++}; col++ }
 /^[0-9a-f]+\.[0-9a-f]+/ {
   match($0,/^[0-9a-f]+/);
   pool=substr($0, RSTART, RLENGTH);
   poollist[pool]=0;
   up=$col; i=0; RSTART=0; RLENGTH=0; delete osds;
   while (match(up,/[0-9]+/)>0) {
     osds[++i]=substr(up,RSTART,RLENGTH);
     up=substr(up, RSTART+RLENGTH)
   }
   for (i in osds) { array[osds[i],pool]++; osdlist[osds[i]] }
}
END {
  printf("\n");
  printf("pool :\t"); for (i in poollist) printf("%s\t",i); printf("| SUM \n");
  for (i in poollist) printf("--------"); printf("----------------\n");
  for (i in osdlist) {
    printf("osd.%i\t", i); sum=0;
    for (j in poollist) { printf("%i\t", array[i,j]); sum+=array[i,j]; sumpool[j]+=array[i,j] }
    printf("| %i\n",sum)
  }
  for (i in poollist) printf("--------"); printf("----------------\n");
  printf("SUM :\t"); for (i in poollist) printf("%s\t",sumpool[i]); printf("|\n");
}'
```

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

- [docs - configuring pools](https://rook.io/docs/rook/v1.19/Storage-Configuration/Advanced/ceph-configuration/#configuring-pools)
- [docs - monitoring osds & pgs](https://docs.ceph.com/en/latest/rados/operations/monitoring-osd-pg/)
- [docs - placement groups](https://docs.ceph.com/en/latest/rados/operations/placement-groups/#a-preselection-of-pg-num)
- [stackoverflow](https://stackoverflow.com/questions/39589696/ceph-too-many-pgs-per-osd-all-you-need-to-know)
- [cephnotes](http://cephnotes.ksperis.com/blog/2015/02/23/get-the-number-of-placement-groups-per-osd)
- [pgcalc](https://old.ceph.com/pgcalc/)

### BlueStore slow operations

When you see `BLUESTORE_SLOW_OP_ALERT`, it is triggered by `log_latency_fn` messages in OSD logs.
A common example is `_txc_committed_kv` stalls (KV commit latency).
A single slow-op within the default 24h lifetime can keep the alert active.

Identify the slow-op line (example from OSD logs):

```sh
kubectl -n rook-ceph logs deploy/rook-ceph-osd-0 --since=24h | grep -i 'log_latency.*slow operation'
```

If the alert is noisy but workloads are healthy, adjust the slow-op threshold in Ceph config.
This repo manages it via `cephClusterSpec.cephConfig.global` in the rook-ceph-cluster HelmRelease.
To change live from toolbox instead:

```sh
ceph config set global bluestore_slow_ops_warn_threshold 5 # 5 ops
ceph config set global bluestore_slow_ops_warn_lifetime 86400 # in 24h
```

#### Diagnose the issue

Check RocksDB and BlueStore metrics for affected OSDs from rook-ceph-tools:

```sh
# Check compaction queue and write delays
ceph tell osd.0 perf dump | jq '.rocksdb | {compact_queue_len, compact_running, rocksdb_write_delay_time}'

# Check BlueStore KV latencies
ceph tell osd.0 perf dump | jq '.bluestore | {kv_flush_lat, kv_final_lat, kv_sync_lat}'
```

Look for:

- `compact_queue_len` > 0 (compactions queued up)
- `compact_running` > 0 for extended periods
- High `rocksdb_write_delay_time` avgtime
- High `kv_flush_lat` or `kv_sync_lat` avgtime (>5ms is concerning)

#### Force compaction

If RocksDB has a backlog, manually trigger compaction:

```sh
ceph tell osd.0 compact
ceph tell osd.1 compact
```

Watch OSD logs to confirm compaction completes:

```sh
kubectl -n rook-ceph logs deploy/rook-ceph-osd-0 --tail=100 | grep -i 'rocksdb\|compact'
```

The warning should clear automatically once the slow-op counter stops incrementing.

[docs - bluestore config](https://docs.ceph.com/en/latest/rados/configuration/bluestore-config-ref/) [docs - perf counters](https://docs.ceph.com/en/latest/dev/perf_counters/)

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

Prefer running the Ansible playbook across all k8s nodes:

```sh
ansible-playbook -i ./ansible/inventory/hosts.yaml ./ansible/playbooks/node-cruft-cleanup.yaml --become
```

Manual cleanup commands:

```sh
# if /var/lib/journal is the problem, rotate and vacuum
sudo systemctl kill --kill-who=main --signal=SIGUSR2 systemd-journald.service
sudo journalctl --vacuum-size=50M
```

#### Clean up unused images

```sh
sudo k3s crictl rmi --prune
```

#### Restart pods

Restart `mon`, `mds`, `rgw`, and `osd` pods

## Remove orphan rbd images

Use the helper script:

```sh
./scripts/rook-rbd-orphan-cleanup.sh
```

Default behavior is `dry-run` and does not mutate cluster state.

Task wrapper is available as `task rook:rbd-orphan-cleanup` (see [task docs](../../../docs/task.md)).

### Common usage

```sh
# dry-run only (default)
task rook:rbd-orphan-cleanup

# move safe candidates to RBD trash (recommended first destructive step)
task rook:rbd-orphan-cleanup -- --mode trash

# hard delete safe candidates
task rook:rbd-orphan-cleanup -- --mode rm

# non-interactive run (for automation)
task rook:rbd-orphan-cleanup -- --mode trash --yes

# include non-CSI image names in candidate list
task rook:rbd-orphan-cleanup -- --include-non-csi
```

Show script options:

```sh
./scripts/rook-rbd-orphan-cleanup.sh --help
```

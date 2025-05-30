# CloudNative Postgres

CloudNative Postgres uses an Operator to watch for new database cluster- and backup- definitions
as provided by CRDs.

## Operator

The operator is deployed via helm release

## Cluster & Backups

S3-compatible storage can be used as a live WAL backup.
Since the native PVC/PV is using k8s-local local-path, the backup should use NAS-based s3.

## Restore

[k8s-at-home discussion](https://discord.com/channels/673534664354430999/1036720267474509885)

> On versioning:
> If you end up with an older cloudnative pg backup (i.e. i have a pg14 one) but you're using a
> newer operator that defaults to newer (i.e. > 15.1), you wont be able to restore as it will whine about versions.
> Add an image tag to the cluster spec to deploy a second cluster with a specifically downgraded ver to restore
> without having to juggle around changing the operator helm etc

## CLI

Install the [kubectl plugin](https://cloudnative-pg.io/documentation/1.18/cnpg-plugin/)

## Updating postgres versions with CNPG

1. Scale down apps using old cluster
2. Ensure old cluster is running
3. Spin up new cluster, pointing `.connectionParameters` to the old cluster
4. Ensure new cluster has a scheduledBackup pointing to it
5. Redirect `ext-postgres-operator` to new cluster (edit the cluster fqdn in the secret)
6. Redirect apps to new cluster
7. Remove the old cluster (remove before scaling up to make sure apps fully switch over)
8. Scale up apps 🤞🏼

Refs:

- [The Current State of Major PostgreSQL Upgrades with CloudNativePG | EDB](https://www.enterprisedb.com/blog/current-state-major-postgresql-upgrades-cloudnativepg-kubernetes)
- [k8s-at-home ref](https://github.com/onedr0p/home-ops/issues/4448#issuecomment-1430440044)

## Archiving failed for

1. Enter postgres shell

   ```sh
   psql
   ```

2. Reset archiver warning

   ```sql
   SELECT pg_stat_reset_shared('archiver');
   ```

Refs:

- [How to "reset" Last Failed WAL? · cloudnative-pg/cloudnative-pg · Discussion #1402](https://github.com/cloudnative-pg/cloudnative-pg/discussions/1402)
- [How monitoring of WAL archiving improves with PostgreSQL 9.4 and pg_stat_archiver | EDB](https://www.enterprisedb.com/blog/how-monitoring-wal-archiving-improves-postgresql-94-and-pgstatarchiver)

# CloudNative Postgres

CloudNative Postgres uses an Operator to watch for new database cluster- and backup- definitions
as provided by CRDs.

## Operator

The operator is deployed via helm release

## Cluster & Backups

Local storage is used by default; S3-compatible storage can be used as a live WAL backup.

## Restore

[k8s-at-home discussion](https://discord.com/channels/673534664354430999/1036720267474509885)

> On versioning:
> If you end up with an older cloudnative pg backup (i.e. i have a pg14 one) but you're using a
> newer operator that defaults to newer (i.e. > 15.1), you wont be able to restore as it will whine about versions.
> Add an image tag to the cluster spec to deploy a second cluster with a specifically downgraded ver to restore
> without having to juggle around changing the operator helm etc

## CLI

Install the [kubectl plugin](https://cloudnative-pg.io/documentation/1.18/cnpg-plugin/)

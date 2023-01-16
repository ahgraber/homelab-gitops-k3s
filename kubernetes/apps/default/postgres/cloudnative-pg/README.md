# CloudNative Postgres

CloudNative Postgres uses an Operator to watch for new database cluster- and backup- definitions
as provided by CRDs.

## Operator

The operator is deployed via helm release

## Cluster & Backups

S3-compatible storage can be used as a live WAL backup.
Since the native PVC/PV is using k8s-local local-path, the backup should use NAS-based s3.

An example of a db deployment can be found in [_example-db](_example-db/)

## Restore

[k8s-at-home discussion](https://discord.com/channels/673534664354430999/1036720267474509885)

## CLI

Install the [kubectl plugin](https://cloudnative-pg.io/documentation/1.15.1/cnpg-plugin/)

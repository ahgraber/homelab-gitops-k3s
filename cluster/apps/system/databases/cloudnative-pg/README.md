# CloudNative Postgres

CloudNative Postgres uses an Operator to watch for new database cluster- and backup- definitions
as provided by CRDs.

## Operator

The operator is deployed via helm release

## Cluster & Backups

The CRDs are deployed as helm releases using dynsix's 'raw' chart to wrap the CRD.
This allows the use of Rook-Ceph ObjectBucketClaims as an S3 stand-in

An example of a db deployment can be found in [_example-db](_example-db/)

## Restore

[k8s-at-home discussion](https://discord.com/channels/673534664354430999/1036720267474509885)

## CLI

Install the [kubectl plugin](https://cloudnative-pg.io/documentation/1.15.1/cnpg-plugin/)

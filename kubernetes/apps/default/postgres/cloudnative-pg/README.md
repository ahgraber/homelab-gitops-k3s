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

> On versioning:
> If you end up with an older cloudnative pg backup (i.e. i have a pg14 one) but you're using a
> newer operator that defaults to newer (i.e. > 15.1), you wont be able to restore as it will whine about versions.
> Add an image tag to the cluster spec to deploy a second cluster with a specifically downgraded ver to restore
> without having to juggle around changing the operator helm etc

## CLI

Install the [kubectl plugin](https://cloudnative-pg.io/documentation/1.18/cnpg-plugin/)

## Updating CNPG

[ref](https://github.com/onedr0p/home-ops/issues/4448#issuecomment-1430440044)

> @bjw-s presents: "A cnpg database migration in two commits":
>
> Preamble: scale down any workloads that are connected to the existing cluster
> Act 1, spinning up the new cluster alongside the old: bjw-s/home-ops@0a26675 (you can probably determine what you need to uncomment there)
> Intermezzo: Grab some coffee, or do as I did and watch kubectl output like a hawk
> Act 2, remove the old cluster: bjw-s/home-ops@0f656ce

# README

CockroachDB is a distributed SQL database designed for speed, scale, and survival.

## Installation

Install using [CockroachDB operator](https://github.com/cockroachdb/cockroach-operator).
The crds may have to be patched via kustomize to allow flags for topology and tolerations.
The actual deployment is managed in [manifest.yaml](manifest.yaml)

## [Compatibility](https://www.cockroachlabs.com/docs/v21.1/postgresql-compatibility.html)

CockroachDB supports the PostgreSQL wire protocol and the majority of PostgreSQL syntax.
This means that existing applications built on PostgreSQL can often be migrated to CockroachDB without changing application code.

CockroachDB is wire-compatible with PostgreSQL 13 and works with majority of PostgreSQL database tools.

## Backups

[Full backups](https://www.cockroachlabs.com/docs/v21.2/take-full-and-incremental-backups#full-backups) are supported on non-Enterprise instances
[Scheduling](https://www.cockroachlabs.com/docs/v21.2/manage-a-backup-schedule) regular backups is recommended

```sql
CREATE SCHEDULE IF NOT EXISTS daily
  FOR BACKUP INTO 's3://truenas.ninerealmlabs.com:9000?AWS_ACCESS_KEY_ID={SECRET_S3_ACCESS_KEY}&AWS_SECRET_ACCESS_KEY={SECRET_S3_SECRET_KEY}'
    RECURRING '@daily'
    FULL BACKUP ALWAYS
    WITH SCHEDULE OPTIONS first_run = 'now';
```

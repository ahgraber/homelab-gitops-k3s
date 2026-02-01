# [Mealie](https://nightly.mealie.io/)

A self-hosted recipe manager and meal planner with a RestAPI backend and a r
eactive frontend application built in Vue for a pleasant user experience for the whole family.

## Long-running queries

To find long-running queries, run:

```sql
SELECT
  pid,
  now() - pg_stat_activity.query_start AS duration,
  query,
  state
FROM pg_stat_activity
WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes';
```

To (safely) cancel query:

```sql
SELECT pg_cancel_backend(<pid>);
```

To force-terminate:

```sql
SELECT pg_terminate_backend(<pid>);
```

## Postgres -> SQLite migration

Mealie supports SQLite and can migrate from Postgres using the built-in backup and restore process.

High-level steps:

1. Take a Mealie backup (Admin UI: Settings -> Backups).
2. Switch the deployment to SQLite and start Mealie once (creates the schema).
3. Restore the backup in the new SQLite-backed instance.

Notes:

- SQLite stores data under `/app/data`.
- SQLite is recommended for smaller deployments, but network storage can be more sensitive to WAL locking than local disks.
  Consider enabling WAL via `SQLITE_MIGRATE_JOURNAL_WAL=true` on Ceph/NAS-backed PVCs.

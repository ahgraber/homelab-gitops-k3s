# SQLite + Litestream

This repo can run SQLite-backed apps on Rook-Ceph PVCs and replicate them to external S3 using Litestream.

## Assumptions

- SQLite DB lives on a single-writer PVC (RWO).
  Rook-Ceph RBD is OK.
- Only one pod writes to the DB at a time.
- External S3 (AWS or compatible) is reachable from the cluster.

## Litestream pattern (sidecar + init restore)

- Add a Litestream sidecar container to the pod.
- Mount the same PVC as the app container so Litestream can read the DB.
- Mount `/etc/litestream.yml` from a ConfigMap.
- Restore on boot with an initContainer.

Litestream expands environment variables in the config file, so you can keep credentials in Secrets and reference `${VAR}` in `litestream.yml`.
It also supports directory replication with a `dir` + `pattern` when the DB file name is not known ahead of time.

### Example config

```yaml
# /etc/litestream.yml
# Environment variables such as AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
# are expanded at startup.

dbs:
  - path: /var/opt/memos/memos_prod.db
    replica:
      url: s3://${LITESTREAM_S3_BUCKET}/memos
      access-key-id: ${AWS_ACCESS_KEY_ID}
      secret-access-key: ${AWS_SECRET_ACCESS_KEY}
  - dir: /app/data
    pattern: '*.db'
    replica:
      url: s3://${LITESTREAM_S3_BUCKET}/mealie
      access-key-id: ${AWS_ACCESS_KEY_ID}
      secret-access-key: ${AWS_SECRET_ACCESS_KEY}
```

### Secret requirements

Create a Secret (or ExternalSecret) named `litestream-s3` in the app namespace with at least:

```text
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
LITESTREAM_S3_BUCKET
```

Prefer Bitwarden/ExternalSecrets for credentials and keep SOPS only for bootstrap cases.

### Init restore command

Use Litestream's conditional restore flags so the pod is idempotent when no backups exist yet.

```bash
litestream restore -config /etc/litestream.yml \
  -if-db-not-exists -if-replica-exists /var/opt/memos/memos_prod.db
```

## Postgres -> SQLite migration (generic data mover)

This repo includes a generic data-only migration helper:

```text
./scripts/pg-to-sqlite.sh -c "postgres://user:pass@host:5432/db" \
  -s /path/to/app.sqlite
```

What it does:

- Creates a timestamped `pg_dump` backup (custom format)
- Copies the SQLite file before import (if it exists)
- Exports data-only SQL from Postgres and strips Postgres-specific statements
- Imports table data into the _existing_ SQLite schema
- Verifies SQLite integrity at the end

This is designed for apps that can create their SQLite schema on first boot (e.g., start the app once with SQLite, then stop it and run the import).
The script does not generate SQLite schemas or constraints.
It may require manual fixes for Postgres-specific types (JSON, arrays, enums) and expressions that SQLite doesn't support.

### Where to run it

- **Locally** (recommended): run on your workstation with network access to
  Postgres and the SQLite file (copy it from the PVC first).
- **In-cluster**: run as a Kubernetes Job with a toolbox image that includes
  `pg_dump` and `sqlite3`, mounting the target PVC and pointing the Postgres
  connection at the service.

### Recoverability

You can always restore the Postgres dump with `pg_restore` or revert to the
SQLite backup copy created by the script if anything goes wrong.

## Memos and Mealie notes

- Memos uses `MEMOS_DRIVER` and `MEMOS_DATA`.
  The SQLite database is created at `{MEMOS_DATA}/memos_prod.db` by default.
- Mealie defaults to SQLite and stores all data under `/app/data`.
  Enabling WAL is recommended on Ceph/NAS to reduce locking issues.
  Mealie notes that NAS-backed storage can be more sensitive to SQLite locking than Postgres.

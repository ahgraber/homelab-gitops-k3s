#!/usr/bin/env bash
# Description: Migrate data from Postgres to an existing SQLite database
# Usage: ./scripts/pg-to-sqlite.sh -c <postgres_url> -s <sqlite_db_path> [-o <output_dir>]
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: ./scripts/pg-to-sqlite.sh -c <postgres_url> -s <sqlite_db_path> [-o <output_dir>]

Options:
  -c  Postgres connection string, e.g. postgres://user:pass@host:5432/db
  -s  SQLite database file path (must exist; schema should already be created)
  -o  Output directory for backups (default: ./_migrations)
  -h  Show this help
USAGE
}

PG_URL=""
SQLITE_DB=""
OUT_DIR="./_migrations"

while getopts ":c:s:o:h" opt; do
  case "${opt}" in
    c) PG_URL="${OPTARG}" ;;
    s) SQLITE_DB="${OPTARG}" ;;
    o) OUT_DIR="${OPTARG}" ;;
    h) usage; exit 0 ;;
    *) usage; exit 1 ;;
  esac
done

if [[ -z "${PG_URL}" || -z "${SQLITE_DB}" ]]; then
  usage
  exit 1
fi

if [[ ! -f "${SQLITE_DB}" ]]; then
  echo "SQLite database not found: ${SQLITE_DB}" >&2
  echo "Create the SQLite DB (and schema) by starting the app once, then stop it." >&2
  exit 1
fi

mkdir -p "${OUT_DIR}"

TS=$(date -u +%Y%m%dT%H%M%SZ)
PG_DUMP_FILE="${OUT_DIR}/pg_dump_${TS}.dump"
PG_DUMP_SQL_RAW="${OUT_DIR}/pg_data_${TS}.raw.sql"
SQLITE_BACKUP_FILE="${OUT_DIR}/$(basename "${SQLITE_DB}").${TS}.bak"
SQLITE_IMPORT_FILE="${OUT_DIR}/pg_data_${TS}.sql"

command -v pg_dump >/dev/null 2>&1 || { echo "pg_dump not found" >&2; exit 1; }
command -v sqlite3 >/dev/null 2>&1 || { echo "sqlite3 not found" >&2; exit 1; }

# 1) Backup Postgres
pg_dump --format=custom --no-owner --no-acl --file "${PG_DUMP_FILE}" "${PG_URL}"

# 2) Backup SQLite
cp -a "${SQLITE_DB}" "${SQLITE_BACKUP_FILE}"

# 3) Export Postgres data-only SQL
#    This assumes the SQLite schema already exists and is compatible.
pg_dump --data-only --column-inserts --disable-triggers --no-owner --no-acl \
  --file "${PG_DUMP_SQL_RAW}" "${PG_URL}"

# 4) Strip Postgres-specific statements so SQLite can parse the file.
sed -E \
  -e '/^SET /d' \
  -e '/^SELECT pg_catalog\.setval/d' \
  -e '/^ALTER TABLE .* DISABLE TRIGGER/d' \
  -e '/^ALTER TABLE .* ENABLE TRIGGER/d' \
  -e '/^COMMENT ON /d' \
  -e '/^--/d' \
  "${PG_DUMP_SQL_RAW}" > "${SQLITE_IMPORT_FILE}"

# 5) Import into SQLite
sqlite3 "${SQLITE_DB}" <<SQL
PRAGMA foreign_keys=OFF;
BEGIN;
.read '${SQLITE_IMPORT_FILE}'
COMMIT;
PRAGMA foreign_keys=ON;
SQL

# 6) Integrity check
sqlite3 "${SQLITE_DB}" "PRAGMA integrity_check;"

echo "Done. Backups:"
echo "- Postgres dump: ${PG_DUMP_FILE}"
echo "- SQLite backup: ${SQLITE_BACKUP_FILE}"

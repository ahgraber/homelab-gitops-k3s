#!/bin/bash
----------
kubectl exec -it postgresql-postgresql-0 -n backend -- /bin/bash

----------
# create dbs
export ROOT_PWD="${SECRET_DB_ROOT_PWD}"
export USER_PWD="${SECRET_DB_USER_PWD}"
# echo "ROOT_PWD=$ROOT_PWD"
# echo "USER_PWD=$USER_PWD"

function initdb {
    echo "Creating \"$1\" user and database"

    # note: if this presents problems in the future, look into heredoc indentations
    psql "postgresql://postgres:$POSTGRES_PASSWORD@localhost:5432" -e <<EOSQL
CREATE USER $1 WITH LOGIN PASSWORD '$USER_PWD';
CREATE DATABASE "$1";
GRANT ALL PRIVILEGES ON DATABASE "$1" TO "$1";
EOSQL
}

# initialize users + databases
initdb "vaultwarden"
initdb "authentik"
initdb "mealie"
initdb "nextcloud"

unset ROOT_PWD
unset USER_PWD

----------
# base backup script
echo 'Making .pgpass file...'
cat > /bitnami/postgresql/.pgpass << EOF
*:*:replication:postgres:***REMOVED***
EOF
chmod 0600 /bitnami/postgresql/.pgpass

echo 'Making backup directories if they do not exist...'
mkdir -p /mnt/backup/{backup.d,incremental.d}

echo 'Checking backup directory...'
if [ -z "ls -A /mnt/backup/backup.d)" ]; then
    echo "Base backup location /mnt/backup/backup.d is empty, running full backup..."
    PGPASSFILE=/bitnami/postgresql/.pgpass pg_basebackup -U postgres --no-password -D /mnt/backup/backup.d
fi


----------
# incremental backup
echo 'Making .pgpass file...'
kubectl exec postgresql-postgresql-0 -n postgresql -- /bin/bash -c '\
cat > /bitnami/postgresql/.pgpass << EOF
*:*:replication:postgres:***REMOVED***
EOF
chmod 0600 /bitnami/postgresql/.pgpass
'

echo 'Making monthly backup directory...'
BASEDIR="/mnt/backup/backup-$(date +"%Y-%m-%d")"
kubectl exec postgresql-postgresql-0 -n postgresql -- /bin/bash -c "mkdir -p $BASEDIR"

echo "Running monthly backup..."
kubectl exec postgresql-postgresql-0 -n postgresql -- /bin/bash -c "PGPASSFILE=/bitnami/postgresql/.pgpass pg_basebackup -U postgres --no-password -D $BASEDIR"
echo 'Backup process completed.'

# note:
# .pgpass not accepted from kubectl /bash -c or from interactive


---------
SELECT *,
current_setting('archive_mode')::BOOLEAN
    AND (last_failed_wal IS NULL
#             OR last_failed_wal <= last_archived_wal)
        AS is_archiving,
    CAST (archived_count AS NUMERIC)
        / EXTRACT (EPOCH FROM age(now(), stats_reset))
        AS current_archived_wals_per_second
FROM pg_stat_archiver;



-----------
# delete released PVs
kubectl get pv | grep Released | awk '$1 {print$1}' | while read vol; do kubectl delete pv/${vol}; done

# reset app
helm delete postgresql -n backend \
&& flux delete hr postgresql -n backend -s \
&& kubectl delete -f ./cluster/apps/backend/postgresql/pvc.yaml \
&& kubectl get pv | grep Released | awk '$1 {print$1}' | while read vol; do kubectl delete pv/${vol}; done \
&& flux reconcile source git flux-system \
&& flux reconcile kustomization apps
sleep 30
kubectl get kustomization -A
flux get hr -A

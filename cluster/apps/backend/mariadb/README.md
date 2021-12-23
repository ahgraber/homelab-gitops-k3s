# README

MariaDB is an MySQL-compatible open source relational database.

## Installation

Install using Helm chart. Modify [configMap-init.yaml](configMap-init.yaml) to include any
databases/users that need to be create on initial install (see `initdb` command at end).

If additional databases are required after install, run below commands:

1. Enter postgresql pod with interactive bash

   ```sh
   kubectl exec -it mariadb-0 -n mariadb -- /bin/bash
   ```

2. Create DB and User (Note: may have to change direnv-passed variables)

   ```sh
   # DB and User name
   export ROOT_PWD="${SECRET_DB_ROOT_PWD}"
   export USER_PWD="${SECRET_DB_USER_PWD}"
   DB=""

   function initdb {
   echo "Creating \"$1\" user and database"

   # note: if this presents problems in the future, look into heredoc indentations
   /opt/bitnami/mariadb/bin/mysql --port=3306 --user="root" --password="$ROOT_PWD" -v <<EOSQL
   CREATE USER '$1'@'%' IDENTIFIED BY '$USER_PWD';
   GRANT USAGE ON *.* TO '$1'@'%' REQUIRE NONE WITH \
     MAX_QUERIES_PER_HOUR 0 \
     MAX_CONNECTIONS_PER_HOUR 0 \
     MAX_UPDATES_PER_HOUR 0 \
     MAX_USER_CONNECTIONS 0;
   CREATE DATABASE IF NOT EXISTS \`$1\`;
   GRANT ALL PRIVILEGES ON \`$1\`.* TO '$1'@'%';
   FLUSH PRIVILEGES;
   EOSQL
   }

   initdb "${DB}"
   unset DB
   unset ROOT_PWD
   unset USER_PWD
   ```

## Backups

[Mariadb backup reference](https://mariadb.com/kb/en/incremental-backup-and-restore-with-mariabackup/)

Backups are handled by a [CronJob](cronjob-backup.yaml) that runs an incremental backup once per
day. Backups are saved in a distinct [PVC](pvc.yaml) so Velero can run restic against the backups
only.

## Restore

### Prepare Restore

In order to restore a backup to the database, you first need to apply the incremental backups to the
base full backup. This is done using the `--prepare` command option.

```sh
# First, prepare the base backup
mariabackup --prepare --target-dir=/mnt/backup/backup.d

# Then, apply the incremental changes to the base full backup
# This brings the base backup into sync with the increment
increments=$(find /mnt/backup/increment.d/ -maxdepth 1 -type d)
IFS=$'\n' increments=($(sort <<<"${increments[*]}")); unset IFS
for incr in ${increments[@]}; do
    mariabackup --prepare --target-dir=/mnt/backup/backup.d --incremental-dir=${incr}
done
```

### Implement Restore

```sh
# empty datadir
cd /bitnami/mariadb/data
rm -rf *
# restore backup
mariabackup --copy-back --target-dir=/mnt/backup/backup.d/
# restore permissions
chown -R 1001 /bitnami/mariadb/data/
```

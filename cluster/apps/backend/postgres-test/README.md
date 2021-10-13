# postgresql

PostgreSQL is a powerful, open source object-relational database system that uses and extends the SQL language combined with many features that safely store and scale the most complicated data workloads

## Installation

Install using Helm chart.
Modify [configMap-conf.yaml](configMap-conf.yaml) to update postgresql.conf parameters.
Modify [configMap-init.yaml](configMap-init.yaml) to include any databases/users that need to be create on initial install (see `initdb` command at end).

----------

If additional databases are required after install, run below commands:

1. Enter postgresql pod with interactive bash

   ```sh
   kubectl exec -it postgresql-postgresql-0 -n postgresql -- /bin/bash
   ```

2. Create DB and User (Note: may have to change direnv-passed variables)

   ```sh
   # DB and User name
   export ROOT_PWD="${SECRETS_DB_ROOT_PWD}"
   export USER_PWD="${SECRETS_DB_USER_PWD}"
   DB=""

   function initdb {
   echo "Creating \"$1\" user and database"

   # note: if this presents problems in the future, look into heredoc indentations
   psql "postgresql://postgres:$ROOT_PWD@localhost:5432" -e <<EOSQL
   CREATE USER $1 WITH LOGIN PASSWORD '$USER_PWD';
   CREATE DATABASE "$1";
   GRANT ALL PRIVILEGES ON DATABASE "$1" TO "$1";
   EOSQL
   }

   initdb "${DB}"
   unset DB
   unset ROOT_PWD
   unset USER_PWD
   ```

### Configuration files

Configuration files are found in `/opt/bitnami/postgresql/conf/`

## Backups

[Postgresql backup reference](https://www.postgresql.org/docs/14/continuous-archiving.html)
[Postgresql WAL archive debug](https://blog.dbi-services.com/__trashed-3/)
[Postgresql WAL archive / backup](https://www.zimmi.cz/posts/2018/postgresql-backup-and-recovery-orchestration-wal-archiving/)

Incremental backups are managed by postgresql's integrated WAL archive.

> We can check archive settings with:
>
> ```sh
> kubectl exec -it postgresql-postgresql-0 -n postgresql -- /bin/bash
> # get archive settings
> psql -U postgres -c "SHOW archive_mode"
> psql -U postgres -c "SHOW archive_command"
> psql -U postgres -c "SHOW archive_timeout"
> # get archive stats
> psql -U postgres -c "SELECT * FROM pg_stat_archiver"
>
># Test archive_command with to force the current WAL segment to be closed and a new one to be created
> psql -U postgres -c "SELECT pg_switch_wal()"
> ````

Incremental backups supplemented by a monthly backup that is handled by a [CronJob](cronjob-backup.yaml).
Backups are saved in a distinct [PVC](pvc.yaml) so Velero can run restic against the backups only.

### Restore

***Point-In-Time-Recovery (PITR)***
PITR refers to PostgreSQL’s ability to start from the restore of a full backup, then progressively fetch and apply archived WAL files up to a specified timestamp.

To do this, we have to create a file called “recovery.conf” in the restored cluster data directory and start up a Postgres server for that data directory. The recovery.conf file contains the target timestamp, and looks like this:

```sh
# stop the server
pg_ctl -D /bitnami/postgres/data stop
```

```ini
restore_command = 'cp /mnt/backup/backup.d/pg_wal/%f "%p"'
recovery_target_time = '2021-010-01 20:00:00'
```

The restore_command specifies how to fetch a WAL file required by PostgreSQL. It is the inverse of archive_command. The recovery_target_time specifies the time until when we need the changes.

When a PostgreSQL server process starts up and discovers a `recovery.conf` file in the data directory,
it starts up in a special mode called “recovery mode”. When in recovery mode, client connections are refused.
Postgres fetches WAL files and applies them until the recovery target (in this case, changes up to the specified timestamp) is achieved.

```sh
# start the server; will start in recovery mode
pg_ctl -D /bitnami/postgres/data start
```

When the target is achieved, the server by default pauses WAL replay (other actions are possible).
At this point, you are supposed to examine the state of the restore and if everything looks ok,
unpause to exit recovery mode and continue normal operation.

```sh
# enter sql prompt to review data
psql "postgresql://postgres:${SECRET_DB_ROOT_PWD}@localhost:5432"
```

```sql
-- examine data
select count(*) from tbl1;

-- exit recovery
select pg_wal_replay_resume();
```

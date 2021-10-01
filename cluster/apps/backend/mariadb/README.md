# README

[Mariadb backup reference](https://mariadb.com/kb/en/incremental-backup-and-restore-with-mariabackup/)

## Backups

Backups are handled by a [CronJob](cronjob-backup.yaml) that runs an incremental backup once per day.
Backups are saved in a distinct [PVC](pvc.yaml) so Velero can run restic against the backups only.

## Restore

### Prepare

In order to restore a backup to the database, you first need to apply the incremental backups to the base full backup.
This is done using the `--prepare` command option.

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

### Restore

```sh
# empty datadir
cd /bitnami/mariadb/data
rm -rf *
# restore backup
mariabackup --copy-back --target-dir=/mnt/backup/backup.d/
# restore permissions
chown -R 1001 /bitnami/mariadb/data/
```

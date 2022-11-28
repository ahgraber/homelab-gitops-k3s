# [Kopia](https://kopia.io/docs/getting-started/)

Kopia is a storage-agnostic fast and secure open-source backup/restore tool.

## Prerequisites

### NFS Setup (on Truenas SCALE)

1. Create `kopia` user and associate with groups `adm,sudo,www-data,backup,builtin_users`
2. Ensure global NFS Settings:
   1. Enable NFSv4
   2. NFSv3 ownership model for NFSv4
   3. Allow non-root mount
3. Create `kopia` share directory
4. Change permissions on share directory: `chmod -R 0777 /path/to/share`
5. Change ownership on share directory: `chown -R kopia:www-data /path/to/share`
6. Set up `kopia` directory as NFS share
   1. Add appropriate subnets to `Authorized Networks`
   2. Set `maproot user` to `kopia`
   3. Set `maproot group` to `www-data`

## Kopia on K8s

Since `kopia` is deployed as a container, it can only back up volumes that are mounted to the container.
The webui, therefore, is not used to set up snapshots, but simply for snapshot introspection and review.
Therefore, the should not be expected to start unless the repository has been established by a snapshot job.

See the [poor-man's backup](#poor-mans-backup) solution for automated snapshotting of PVCs.

### Poor-Man's Backup

The "Poor-Man's Backup" solution depends on Kyverno
to automatically generate cronjobs that will run kopia snapshots
on PVCs with the label `snapshot.home.arpa/enabled="true"`

1. The [snapshot-cronjob-controller.yaml](./jobs/snapshot-cronjob-controller.yaml) identifies PVCs
   with the appropriate labels and generates a cronjob
2. The cronjob runs daily and creates a kopia snapshot
3. Kopia snapshots are saved to local NAS on an NFS share
4. Kopia snapshots are [backed up](#offsite-backups) to an offsite, s3-compatible blob

#### Offsite Backups

Backups of snapshots can be scheduled in the `jobs/` subdir with example to send to Backblaze B2

#### Restore

see also: [Restore Tasks](../../../../.taskfiles/RestoreTasks.yaml)

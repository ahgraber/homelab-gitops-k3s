# [Kopia](https://kopia.io/docs/getting-started/)

Kopia is a storage-agnostic fast and secure open-source backup/restore tool.

## Poor-Man's Backup

The "Poor-Man's Backup" solution is tightly-integrated with Kyverno,
which provides the automation to generate the cronjobs that will trigger Kopia snapshots
on PVCs with the label `snapshot.home.arpa/enabled="true"`

Note that this tight integration means that the kyverno-generate cronjobs will initialize the kopia repositories;
without the kyverno policy in place, the Kopia HelmRelease will appear to fail.

1. Kopia is started and waits for a repository to be initialized
2. Kyvero policy triggers a cronjob to create a [snapshot](#snapshots), which initializes the repository if required
3. Kopia snapshots are saved to local NAS on an NFS share
4. Kopia snapshots are [backed up](#offsite-backups) to an offsite, s3-compatible blob

## NFS Setup (on Truenas SCALE)

1. Create directory to be shared
2. Change permissions on share directory: `chmod -R 0777 /path/to/share`
3. Change ownership on share directory: `chown -R kopia:www-data /path/to/share`
4. Create `kopia` user and associate with groups `adm,sudo,www-data,backup,builtin_users`
5. Ensure NFS Settings
   1. Enable NFSv4
   2. NFSv3 ownership model for NFSv4
   3. Allow non-root mount
6. Set up `kopia` nfs share
   1. Add appropriate subnets to `Authorized Networks`
   2. Set `maproot user` to `kopia`
   3. Set `maproot group` to `www-data`

## Snapshots

See kyverno policy [snapshot-cronjob-controller.yaml](./jobs/snapshot-cronjob-controller.yaml)

## Offsite Backups

Backups of snapshots can be scheduled in the `jobs/` subdir with example to send to Backblaze B2

## Restore

see also: [Restore Tasks](../../../../../homelab-gitops-k3s/.taskfiles/RestoreTasks.yaml)

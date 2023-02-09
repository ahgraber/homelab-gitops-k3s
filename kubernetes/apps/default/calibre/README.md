# Calibre

ebook editor and manager

## Prerequisites

Configure `books` directory and nfs share on NAS

## Backup

`books` share backup should be managed by NAS.
This means that there will be no k8s-native CSI snapshots, and therefore VolSync backups are not required.

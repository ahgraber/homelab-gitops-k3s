# [Jelu](https://github.com/bayang/jelu)

Self-hosted reading tracker that keeps a local library of finished, in-progress, and planned books while supporting Goodreads/CSV imports and metadata fetches.
The upstream container already ships with the calibre metadata helper and stores all state inside a directory that we back by Rook-Ceph so it can be synced with VolSync.

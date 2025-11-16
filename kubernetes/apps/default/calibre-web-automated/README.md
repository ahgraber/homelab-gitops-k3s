# [Calibre Web Automated](https://github.com/crocodilestick/calibre-web-automated)

Automated Calibre Web deployment that watches an ingest directory and keeps a self-hosted Calibre library up to date. This setup uses a CephFS-backed `calibre-library` PVC so other automation jobs (like calibre-web-automated-downloader or OpenBooks) can exchange files through the same shared volume.

## Notes

- Persists both the application config and the Calibre library onto Ceph storage. The config ( `calibre-web-automated-config` ) is RWO, while the shared library volume uses RWX so additional apps can drop downloads into `/cwa-book-ingest`.
  .

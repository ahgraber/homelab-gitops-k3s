# [Calibre Web Downloader](https://github.com/SpotNic/calibre-web-automated-book-downloader)

Automates discovery and downloading of ebooks for Calibre Web Automated. Downloads are pushed into the shared `calibre-library` PVC so the main Calibre instance can ingest them automatically.

## Notes

- Uses the same CephFS-backed library PVC as Calibre Web Automated (mounted at `/book-intake`).
- Includes the Cloudflare bypass sidecar (via `flaresolverr`) so Annas Archive requests can complete reliably.
- Relies on the `calibre-web-automated` deployment and the shared `calibre-library` PVC being present before it reconciles.

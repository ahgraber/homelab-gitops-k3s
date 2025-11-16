# [OpenBooks](https://github.com/evan-buss/openbooks)

IRC-based ebook search and download client. Downloads flow into the shared `calibre-library` PVC so Calibre Web Automated can ingest them after retrieval.

## Notes

- Published internally at `https://openbooks.${SECRET_DOMAIN}` via Envoy Gateway.
- Drops downloads directly into `/books` which maps to the `calibre-library` PVC sub-path dedicated to ingest operations.
- Relies on the shared CephFS PVC provisioned by the Calibre Web Automated app.

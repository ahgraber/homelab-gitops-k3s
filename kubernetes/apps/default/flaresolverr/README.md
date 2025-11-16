# [FlareSolverr](https://github.com/FlareSolverr/FlareSolverr)

Headless browser service that bypasses Cloudflare protections for other automation apps (Calibre Web Downloader, OpenBooks, etc.). Exposed only as a ClusterIP service inside the default namespace.

## Notes

- Stateless and does not require persistent storage.
- Requests modest CPU/memory so it can be scheduled on any worker.

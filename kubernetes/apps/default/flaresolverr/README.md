# [FlareSolverr](https://github.com/FlareSolverr/FlareSolverr)

Headless browser service that bypasses Cloudflare protections for other apps.
Exposed only as a ClusterIP service at `http://flaresolverr.default.svc.cluster.local:8191`.

## Notes

- Stateless and does not require persistent storage.
- No authentication; do not expose it through a gateway.
- Supported by mealie (`SCRAPER_FLARESOLVERR_URL`) and shelfmark (`EXT_BYPASSER_URL`); neither is wired to it.

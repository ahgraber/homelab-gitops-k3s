# [Calibre Web Downloader](https://github.com/calibrain/calibre-web-automated-book-downloader)

Automates discovery and downloading of ebooks for Calibre Web Automated.
Downloads are pushed into the shared `calibre-library` PVC so the main Calibre instance can ingest them automatically.

## Notes

- Uses the same CephFS-backed library PVC as Calibre Web Automated (mounted at `/cwa-book-ingest`).
- Includes the Cloudflare bypass sidecar (via `flaresolverr`) so requests can complete reliably.
- Relies on the `calibre-web-automated` deployment and the shared `calibre-library` PVC being present before it reconciles.

## OIDC Integration

Shelfmark OIDC is configured in the app UI.

1. Create an OIDC client in your IdP with callback URL:
   `https://shelfmark.${SECRET_DOMAIN}/api/auth/oidc/callback`
2. Open Shelfmark: `Settings -> Security -> Authentication Method -> OIDC`
3. Set:
   - Discovery URL: `https://auth.${SECRET_DOMAIN}/.well-known/openid-configuration`
   - Client ID: your OIDC client id
   - Client Secret: your OIDC client secret
   - Scopes: `openid email profile`
4. Keep a local admin account available for recovery/fallback login.

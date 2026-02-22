# [Calibre Web Automated](https://github.com/crocodilestick/calibre-web-automated)

Automated Calibre Web deployment that watches an ingest directory and keeps a self-hosted Calibre library up to date.
This setup uses a CephFS-backed `calibre-library` PVC so other automation jobs (like calibre-web-automated-downloader or OpenBooks) can exchange files through the same shared volume.

## Notes

- Persists both the application config and the Calibre library onto Ceph storage.
  The config (`calibre-web-automated-config` ) is RWO, while the shared library volume uses RWX so additional apps can drop downloads into `/cwa-book-ingest`.
- Review the source README - substantial configuration is done manually in-app rather than via deployment configuration.

## OIDC Integration

Shelfmark OIDC is configured in the app UI.

1. Create an OIDC client in your IdP with callback URL:
   `https://calibre.${SECRET_DOMAIN}/api/auth/oidc/callback`
2. Open Calibre: `Basic Configuration -> Feature Configuration -> Login Type -> OIDC`
3. Set:
   - Discovery URL: `https://auth.${SECRET_DOMAIN}/.well-known/openid-configuration`
   - Client ID: your OIDC client id
   - Client Secret: your OIDC client secret
   - Scopes: `openid email profile`
4. Keep a local admin account available for recovery/fallback login.

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

## Troubleshooting

### "Permission denied" when deleting books

Symptom: deleting a book in the web UI fails silently (the book gets an
"archive bit" set / hidden instead of removed) and the pod logs show:

```text
ERROR {cps.helper} Deleting book <id> failed: [Errno 13] Permission denied: '/calibre-library/.../<file>.epub'
```

Cause: inside the pod the two s6 services run as **different UIDs**:

- the web app (`cps.py`, which handles the delete button) runs as **uid 1000** with no capabilities
- the `cwa-ingest-service` (which imports books) runs as **root**

So freshly-ingested files are created `root:1000` with no group-write, and the uid-1000 web process cannot delete them.

Fix (both parts):

1. **Durable:** `UMASK: "002"` is set in the HelmRelease env so the root ingest service creates group-writable files (`0664`/`0775`).
   Combined with the setgid bit that library dirs already carry (group stays `1000`), the uid-1000 web app can then manage them.
   This only affects **future** imports.

2. **One-time repair** of books imported before the fix:

   ```bash
   direnv exec . kubectl exec -n default <cwa-pod> -c app -- \
     chmod -R g+w /calibre-library
   ```

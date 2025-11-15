# [Jelu](https://github.com/bayang/jelu)

Self-hosted reading tracker that keeps a local library of finished, in-progress,
and planned books while supporting Goodreads/CSV imports and metadata fetches.
The upstream container already ships with the calibre metadata helper and stores
all state inside a directory that we back by Rook-Ceph so it can be synced with
VolSync.

## Configuration highlights

- Binds `https://jelu.${SECRET_DOMAIN}` to the external Envoy Gateway.
- Uses the single-file database with `JELU_DATABASE_PATH=/data/database` so the
  complete application state (database, uploads, and imports) lives on the same
  PVC.
- Enables the OAuth2/OIDC flow via Authelia. The client secret is managed in
  `secret-oidc.sops.yaml`; update it whenever you create/rotate the client in
  Authelia.
- Account creation is enabled for OAuth2 logins because Authelia already gates
  access and verifies email addresses.

## Dependencies

- `rook-ceph-cluster` for persistent storage
- `volsync` for warm restores/backups
- `networking/envoy-external` Gateway and Cloudflare tunnel
- Authelia (`auth.${SECRET_DOMAIN}`) for the OIDC provider

## References

- Upstream docs: <https://bayang.github.io/jelu-web/>
- Helm chart base: <https://github.com/bjw-s/helm-charts/tree/main/charts/other/app-template>

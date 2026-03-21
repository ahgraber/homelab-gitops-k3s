# [Actual Budget](https://actualbudget.org/)

Actual Budget is a local-first personal finance tool with optional sync across devices.

- **Image**: `ghcr.io/actualbudget/actual-server`
- **Port**: 5006
- **Ingress**: Internal only (envoy-internal gateway)
- **Storage**: Persistent volume at `/data` (ceph-block via volsync)

## Dependencies

- rook-ceph-cluster (storage)
- volsync (backup/restore)
- authelia (OIDC authentication)

## Authentication (OIDC)

Actual Budget uses OpenID Connect via Authelia for authentication.

### Setup

1. Generate and store the OAuth client secret in 1Password:

   ```bash
   just oauth-secret default actual-budget
   ```

   This generates a random secret + PBKDF2 digest and stores both in 1Password:

   - `op://homelab/default.actual-budget/client-secret` (plaintext, for the app)
   - `op://homelab/security.authelia/ACTUAL_BUDGET_OAUTH_CLIENT_DIGEST` (digest, for Authelia)

2. Verify ExternalSecrets reconcile after deploy.

### Configuration

- **Client ID**: `actual-budget`
- **Redirect URI**: `https://actual-budget.<domain>/openid/callback`
- **Scopes**: `openid email profile`
- **PKCE**: Required (S256)
- **Login method**: OpenID enforced (password login disabled)

## Links

- [Actual Budget Docs](https://actualbudget.org/docs/)
- [Container Image](https://github.com/actualbudget/actual/pkgs/container/actual-server)
- [Source Code](https://github.com/actualbudget/actual)

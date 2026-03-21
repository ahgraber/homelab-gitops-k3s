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

### Configuration

- **Client ID**: `actual-budget`
- **Redirect URI**: `https://budget.<domain>/openid/callback`
- **Scopes**: `openid email profile`
- **PKCE**: Required (S256)
- **Login method**: OpenID enforced (password login disabled)

## Links

- [Actual Budget Docs](https://actualbudget.org/docs/)
- [Container Image](https://github.com/actualbudget/actual/pkgs/container/actual-server)
- [Source Code](https://github.com/actualbudget/actual)

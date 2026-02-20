# 1Password Connect

Runs the 1Password Connect API/sync pair for External Secrets Operator (ESO).

## Purpose

- Deploys 1Password Connect (`connect-api` + `connect-sync`) inside the `external-secrets` namespace.
- Exposes a shared `ClusterSecretStore` named `onepassword`.
- Bootstraps `onepassword-secret` from a `1password` item so credentials can be rotated in 1Password.

## Dependencies

- `external-secrets-operator` must be healthy first.
- `onepassword-secret` bootstrap credentials must exist for first reconciliation.

## Configuration

- `ClusterSecretStore` points to `http://onepassword.external-secrets.svc.cluster.local`.
- Vault priority is configured in `clustersecretstore.yaml`.
- The bootstrap item title is `external-secrets.onepassword` with fields:
  - `OP_CREDENTIALS_JSON`
  - `OP_CONNECT_TOKEN`

## Gotchas

- ESO cannot authenticate to 1Password without the initial `onepassword-secret`; bootstrap this first.
- Keep the vault name in `clustersecretstore.yaml` aligned with your `op://...` references (default: `homelab`).
- Use `op://homelab/<namespace>.<appname>/[section]/<field>` for bootstrap and migration references.
- Use `.` as the preferred namespace/app separator; fallback order is `_`, then `-`.

## References

- <https://github.com/onedr0p/home-ops/tree/main/kubernetes/apps/external-secrets/onepassword>
- <https://external-secrets.io/latest/provider/1password-automation/>
- <https://developer.1password.com/docs/connect/>

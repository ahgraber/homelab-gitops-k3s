# External Secrets Operator

External Secrets Operator (ESO) deployment for the homelab cluster.

## Components

- Namespace: `external-secrets`
- Helm chart: `external-secrets`
- Shared ClusterSecretStore: `onepassword` (managed by `../onepassword/`)
- Example manifests: `../_examples/`

## Bootstrap inputs

Create `onepassword-secret` in the `external-secrets` namespace before first reconciliation.
Expected keys:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: onepassword-secret
  namespace: external-secrets
stringData:
  1password-credentials.json: '...'
  TOKEN: '...'
```

## Usage notes

- Configure app `ExternalSecret` resources to use:
  - `spec.secretStoreRef.kind: ClusterSecretStore`
  - `spec.secretStoreRef.name: onepassword`
- 1Password item title maps to `remoteRef.key`.
- 1Password field label maps to `remoteRef.property`.

## Migration tooling

- See `docs/onepassword-eso-migration-tooling.md` for the migration workflow (`crawl -> push -> externalsecrets`) now targeting 1Password CLI.

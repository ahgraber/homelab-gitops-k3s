# External Secrets Operator for Bitwarden

Phase 1 foundation for migrating SOPS-managed secrets to Bitwarden Secrets Manager via External Secrets Operator (ESO).

## Components

- **Namespace:** `external-secrets`
- **Helm chart:** `external-secrets` (version 0.10.5) with Bitwarden provider and Bitwarden SDK server enabled.
- **ServiceAccounts:** controller (`external-secrets-controller`), webhook (`external-secrets-webhook`), cert controller (`external-secrets-cert-controller`), and SDK server (`bitwarden-sdk-server`).
- **ClusterSecretStore:** `bitwarden-cluster-store` using Bitwarden Secrets Manager credentials stored in the `bitwarden-credentials` Secret (SOPS-encrypted bootstrap).
- **Examples:** reusable `ExternalSecret` and `ClusterExternalSecret` manifests under `./examples/` (not applied by Flux).

## Bootstrap inputs

Create `bitwarden-credentials` in the `external-secrets` namespace before enabling reconcilers. The Secret should be SOPS-encrypted and supplied via bootstrap (e.g., `kubernetes/bootstrap/`). Expected keys:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: bitwarden-credentials
  namespace: external-secrets
stringData:
  clientId: '...'
  clientSecret: '...'
  organizationId: '...'     # Optional if not using organizations
  projectId: '...'          # Optional if not using project scoping
```

## Usage notes

- `ClusterSecretStore` target: `bitwarden-cluster-store`.
- Bitwarden SDK server endpoint: `bitwarden-sdk-server.external-secrets.svc.cluster.local:8087` (HTTP).
- Add namespace-specific ExternalSecrets that point at Bitwarden items in the **Homelab** project; see `examples/` for patterns.
- Monitor `ExternalSecret` and `ClusterSecretStore` conditions after bootstrapping credentials.

# External Secrets Operator for Bitwarden

Phase 1 foundation for migrating SOPS-managed secrets to Bitwarden Secrets Manager via External Secrets Operator (ESO).

## Components

- **Namespace:** `external-secrets`
- **Helm chart:** `external-secrets` (version 0.10.5) with Bitwarden provider and Bitwarden SDK server enabled.
- **ServiceAccounts:** controller (`external-secrets-controller`), webhook (`external-secrets-webhook`), cert controller (`external-secrets-cert-controller`), and SDK server (`bitwarden-sdk-server`).
- **ClusterSecretStore:** `bitwarden-secret-manager` using Bitwarden Secrets Manager credentials stored in the `bitwarden-credentials` Secret (SOPS-encrypted bootstrap).
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

- `ClusterSecretStore` target: `bitwarden-secret-manager`.
- Bitwarden SDK server endpoint: `bitwarden-sdk-server.external-secrets.svc.cluster.local:9998` (HTTPS).
- Add namespace-specific ExternalSecrets that point at Bitwarden items in the **Homelab** project; see `examples/` for patterns.
- Monitor `ExternalSecret` and `ClusterSecretStore` conditions after bootstrapping credentials.

## Operational workflows

### Add or change a secret

1. Add/update the Bitwarden item in the **Homelab** project using the naming convention.
2. Define or update an `ExternalSecret` to map Bitwarden fields to K8s keys.
3. Validate sync by checking `ExternalSecret` conditions and the target Secret contents.

### Rotate credentials

1. Update the Bitwarden item fields (e.g., `password`, `token`).
2. Ensure the `ExternalSecret` refresh interval is acceptable for the rotation window.
3. Watch the `ExternalSecret` status and dependent workloads for successful reloads.

### Troubleshoot sync issues

- Inspect `ExternalSecret` and `ClusterSecretStore` conditions for authentication or lookup errors.
- Confirm `bitwarden-credentials` is present and encrypted in bootstrap and that the SDK server is healthy.
- Verify the Bitwarden item name and field keys match the ExternalSecret `remoteRef` entries.

### Migration tooling

- See `docs/bitwarden-eso-migration-tooling.md` for mapping format and the dry-run migration helper.

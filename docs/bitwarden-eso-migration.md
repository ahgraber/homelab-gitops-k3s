# Bitwarden Secrets Manager migration plan (ESO)

This document outlines a phased migration from SOPS-managed secrets to Bitwarden Secrets Manager using External Secrets Operator (ESO). It is tailored for the current homelab context and assumes the Bitwarden account is a personal (free-tier) Secrets Manager instance.

## Principles and constraints

- Keep a minimal SOPS-encrypted bootstrap only for ESO/Bitwarden client credentials; everything else should transition to Bitwarden.
- Prefer a shared `ClusterSecretStore` for Bitwarden to avoid duplicated configuration; scope access with ESO RBAC and namespaces.
- Deploy ESO in `external-secrets` namespace.
- Use a push-style migration: load secrets into Bitwarden first, then point ExternalSecrets at Bitwarden values. Do not rely on existing SOPS data being present in Bitwarden.
- All ExternalSecrets should target Bitwarden items in the **Homelab** project of the Bitwarden Secrets Manager account to keep scope and access consistent.
- Phase 3 cutovers are organized **namespace-by-namespace** (not app-by-app) to reduce coordination overhead.

## Phase 0: Discovery and design

- Inventory current SOPS secrets (by namespace) and owners; classify shared vs per-app values.
- Decide Bitwarden structure for the **Homelab** project: collections/folders per namespace, item ownership, and any cross-namespace sharing rules.
- Finalize ESO install options: Helm chart values for Bitwarden provider and `bitwarden-sdk-server` enablement; decide on metrics/alerts.
- Define `ClusterSecretStore` shape: name, target namespace (`external-secrets` if required), and `auth.secretRef` wiring to the SOPS-encrypted bootstrap secret.
- Agree on secret naming scheme (see naming conventions) and key mapping for multi-key secrets; confirm how Bitwarden fields map to Kubernetes Secret keys.
- Produce migration inputs: a namespace-scoped inventory (old SOPS path → Bitwarden item/field in Homelab project), and a list of secrets that must remain SOPS-bootstrapped.

### Phase 0 outputs (current repository state)

| Namespace     | App                   | SOPS file path                                                                                     | Notes                               |
| ------------- | --------------------- | -------------------------------------------------------------------------------------------------- | ----------------------------------- |
| bootstrap     | bootstrap             | `kubernetes/bootstrap/age-key.sops.yaml`                                                           | Shared bootstrap (age key).         |
| bootstrap     | bootstrap             | `kubernetes/bootstrap/github-deploy-key.sops.yaml`                                                 | Shared bootstrap (Flux deploy key). |
| cert-manager  | cert-manager          | `kubernetes/apps/cert-manager/cert-manager/issuers/secret.sops.yaml`                               | App-specific issuer credentials.    |
| database      | cloudnative-pg        | `kubernetes/apps/database/cloudnative-pg/cluster/secrets.sops.yaml`                                | App-specific database credentials.  |
| database      | ext-postgres-operator | `kubernetes/apps/database/ext-postgres-operator/app/secret.sops.yaml`                              | Operator credentials.               |
| database      | pgadmin               | `kubernetes/apps/database/pgadmin/app/secret.sops.yaml`                                            | App-specific credentials.           |
| datasci       | cloudnative-pg        | `kubernetes/apps/datasci/postgres/cloudnative-pg/cluster/secrets.sops.yaml`                        | App-specific database credentials.  |
| datasci       | ext-postgres-operator | `kubernetes/apps/datasci/postgres/ext-postgres-operator/app/secret.sops.yaml`                      | Operator credentials.               |
| datasci       | mlflow                | `kubernetes/apps/datasci/mlflow/app/secret.sops.yaml`                                              | App-specific credentials.           |
| datasci       | mlflow                | `kubernetes/apps/datasci/mlflow/app/secret-gateway.sops.yaml`                                      | Gateway-specific credentials.       |
| datasci       | mlflow                | `kubernetes/apps/datasci/mlflow/app/secret-s3.sops.yaml`                                           | Object storage credentials.         |
| default       | calibre-web-automated | `kubernetes/apps/default/calibre-web-automated/app/secret.sops.yaml`                               | App-specific credentials.           |
| default       | calibre-web-automated | `kubernetes/apps/default/calibre-web-automated/app/secret-oidc.sops.yaml`                          | OIDC client credentials.            |
| default       | homebox               | `kubernetes/apps/default/homebox/app/secret.sops.yaml`                                             | App-specific credentials.           |
| default       | homepage              | `kubernetes/apps/default/homepage/app/secret.sops.yaml`                                            | App-specific credentials.           |
| default       | jelu                  | `kubernetes/apps/default/jelu/app/secret-oidc.sops.yaml`                                           | OIDC client credentials.            |
| default       | karakeep              | `kubernetes/apps/default/karakeep/app/secret.sops.yaml`                                            | App-specific credentials.           |
| default       | karakeep              | `kubernetes/apps/default/karakeep/app/secret-oidc.sops.yaml`                                       | OIDC client credentials.            |
| default       | mealie                | `kubernetes/apps/default/mealie/app/secret.sops.yaml`                                              | App-specific credentials.           |
| default       | mealie                | `kubernetes/apps/default/mealie/app/secret-oidc.sops.yaml`                                         | OIDC client credentials.            |
| default       | memos                 | `kubernetes/apps/default/memos/app/secret-oidc.sops.yaml`                                          | OIDC client credentials.            |
| default       | miniflux              | `kubernetes/apps/default/miniflux/app/secret.sops.yaml`                                            | App-specific credentials.           |
| default       | miniflux              | `kubernetes/apps/default/miniflux/app/secret-oidc.sops.yaml`                                       | OIDC client credentials.            |
| default       | picoshare             | `kubernetes/apps/default/picoshare/app/secret.sops.yaml`                                           | App-specific credentials.           |
| debug         | whoami                | `kubernetes/apps/debug/whoami/app/secret-oidc.sops.yaml`                                           | OIDC client credentials.            |
| flux          | flux vars             | `kubernetes/flux/vars/cluster-secrets.sops.yaml`                                                   | Shared bootstrap variables.         |
| flux          | flux vars             | `kubernetes/flux/vars/custom-secrets.sops.yaml`                                                    | Shared customization variables.     |
| flux-system   | flux-system           | `kubernetes/apps/flux-system/addons/webhooks/github/secret.sops.yaml`                              | GitHub webhook secret.              |
| networking    | cloudflared           | `kubernetes/apps/networking/cloudflared/app/secret.sops.yaml`                                      | Tunnel credentials.                 |
| networking    | external-dns          | `kubernetes/apps/networking/external-dns/app/secret.sops.yaml`                                     | DNS provider credentials.           |
| observability | grafana operator      | `kubernetes/apps/observability/grafana/operator/secret.sops.yaml`                                  | App-specific credentials.           |
| observability | grafana operator      | `kubernetes/apps/observability/grafana/operator/secret-oidc.sops.yaml`                             | OIDC client credentials.            |
| observability | kube-prometheus-stack | `kubernetes/apps/observability/kube-prometheus-stack/app/secret-additionalScrapeConfigs.sops.yaml` | Additional scrape configs.          |
| observability | kube-prometheus-stack | `kubernetes/apps/observability/kube-prometheus-stack/app/secret-alertmgrNotifiers.sops.yaml`       | Alertmanager notifiers.             |
| observability | nut-exporter          | `kubernetes/apps/observability/nut-exporter/app/secret.sops.yaml`                                  | App-specific credentials.           |
| security      | authelia              | `kubernetes/apps/security/authelia/app/secret.sops.yaml`                                           | App-specific credentials.           |
| security      | lldap                 | `kubernetes/apps/security/lldap/app/secret.sops.yaml`                                              | Directory credentials.              |
| blog          | hugo                  | `kubernetes/apps/blog/hugo/app/secret.sops.yaml`                                                   | App-specific credentials.           |

Notes:

- All Bitwarden items should live in the **Homelab** project; map Bitwarden folders/collections to the namespaces above to simplify access control.
- Bootstrap SOPS files (`kubernetes/bootstrap/`, `kubernetes/flux/vars/`) remain encrypted even after cutover to feed the `ClusterSecretStore` credentials and Flux variables.
- Namespace inventories above should drive ExternalSecret mappings during Phase 3; use the naming conventions below to keep Bitwarden items aligned with Kubernetes Secret names.

## Phase 1: GitOps foundation in `kubernetes/apps/external-secrets`

Status checklist:

- [x] Add `kubernetes/apps/external-secrets/external-secrets/` (or `kubernetes/apps/external-secrets/`) with Flux Kustomization, HelmRelease, and README.
- [x] Configure HelmRelease for External Secrets Operator with Bitwarden provider enabled and `bitwarden-sdk-server` turned on.
- [ ] Create Namespace manifest (`external-secrets`), ServiceAccount, and RBAC to scope ESO controllers. (Namespace manifest currently defines `security`.)
- [x] Add a `ClusterSecretStore` targeting Bitwarden with references to the bootstrap Secret for client credentials.
- [x] Provide example `ExternalSecret` and `ClusterExternalSecret` manifests for validation.

### Phase 1 outputs (current repository state)

- Namespace, Flux Kustomization, HelmRepository, and HelmRelease for External Secrets Operator live at `kubernetes/apps/external-secrets/external-secrets/` and target the `external-secrets` namespace.
- HelmRelease `external-secrets` (chart `external-secrets` v0.10.5) enables the Bitwarden provider, turns on the Bitwarden SDK server, and wires service accounts for the controller, webhook, cert-controller, and SDK server.
- `ClusterSecretStore` `bitwarden-cluster-store` expects a SOPS-encrypted `bitwarden-credentials` Secret in the `external-secrets` namespace containing `clientId`, `clientSecret`, `organizationId`, and `projectId` keys for the Bitwarden Secrets Manager client.
- Example manifests for namespace-scoped and cluster-scoped syncs are staged (not applied) under `kubernetes/apps/external-secrets/external-secrets/examples/`.

## Phase 2: Migration tooling and documentation

- [x] Author migration guide and automation to translate SOPS secrets to Bitwarden entries:
  - Scripted push: decrypt SOPS locally (`sops --decrypt`) and stream values to Bitwarden via `bws` CLI or API without writing plaintext to disk.
  - Optional in-cluster `PushSecret` pattern: create a temporary K8s Secret, push to Bitwarden, then remove the temporary Secret.
- [x] Define a mapping file format (YAML/JSON) for batch migrations with explicit Bitwarden item names and fields.
- [x] Provide dry-run and idempotency checks (e.g., skip/confirm overwrites, verify item existence).
- [x] Document operational workflows in `kubernetes/apps/external-secrets/external-secrets/README.md` (or equivalent): add/change/reference secret, rotate credentials, and troubleshoot sync issues.

### Phase 2 outputs (current repository state)

- Migration helper: `scripts/bitwarden-eso-migrate.py` (dry-run by default, optional apply with command template).
- Mapping template: `docs/bitwarden-eso-migration-map.example.json`.
- Tooling guide: `docs/bitwarden-eso-migration-tooling.md`.

## Phase 3: Namespace-by-namespace cutover

- [ ] For each namespace:
  - Create/adjust `ExternalSecret` resources that map namespace secrets to Bitwarden items/fields via the shared `ClusterSecretStore`.
  - Update namespace README/kustomizations to reference the new secrets and remove direct SOPS consumption.
  - Validate reconciliation: ensure `ExternalSecret` conditions are healthy and secrets populate correctly before disabling SOPS references.
  - Track completion per-namespace in a migration status matrix.

## Phase 4: Cleanup and legacy handling

- [ ] Keep minimal SOPS bootstrap secrets and legacy Taskfiles for reference, but mark SOPS workflows as deprecated.
- [ ] Update top-level docs to reference Bitwarden + ESO as the default secret management path.
- [ ] Remove unused SOPS secrets from repos once namespaces have fully cut over.
- [ ] Add monitoring/alerting for ESO sync errors and SecretStore readiness.

## Additional recommended milestones

- RBAC hardening: ensure ESO service accounts have only namespace-scoped permissions where possible; restrict `ClusterExternalSecret` usage.
- Reliability: enable PodDisruptionBudgets and resource requests/limits for ESO and the Bitwarden SDK server.
- Observability: ship ESO metrics to the monitoring stack and add alerts for reconciliation failures.
- Resilience drills: practice Bitwarden credential rotation and recover ESO connectivity without downtime.
- Backups: document/export Bitwarden vault backups (as allowed by the free tier) and include recovery steps.

## Naming conventions (Bitwarden + ESO)

- Bitwarden items: `{namespace}-{app}-{purpose}` (e.g., `default-ghost-db`); shared items use `shared-{purpose}`.
- Secret fields: prefer descriptive keys (`username`, `password`, `apiKey`, `token`, `certificate`, `privateKey`).
- Kubernetes Secret names mirror Bitwarden items where possible; avoid generic names like `credentials` or `secret`.
- Collections/folders in Bitwarden map to Kubernetes namespaces for consistent access control.
- ExternalSecret resource names follow `{namespace}-{app}-{source}` (e.g., `default-ghost-bitwarden`).
- ClusterSecretStore name: `bitwarden-cluster-store`; ServiceAccount `external-secrets-controller` (in `external-secrets` namespace).

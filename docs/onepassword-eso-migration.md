# 1Password Connect migration plan (ESO)

This document outlines the migration from SOPS-managed application secrets to
1Password Connect with External Secrets Operator (ESO).

## Principles and constraints

- Keep a minimal SOPS-encrypted bootstrap for cluster bring-up and Flux decryption.
- Use ESO with a shared `ClusterSecretStore` named `onepassword`.
- Deploy ESO and 1Password Connect in `external-secrets` namespace.
- Use a push-style migration: load secrets into 1Password first, then switch workloads to `ExternalSecret`.
- Organize cutovers namespace-by-namespace to reduce coordination overhead.

## Phase 0: Discovery and design

- Inventory current SOPS secrets by namespace and classify shared vs app-specific values.
- Confirm 1Password vault strategy (default vault: `homelab`).
- Confirm naming conventions and field mapping.
- Prepare migration inputs: SOPS path -> 1Password item title/field labels.

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
| network       | cloudflared           | `kubernetes/apps/network/cloudflared/app/secret.sops.yaml`                                         | Tunnel credentials.                 |
| network       | external-dns          | `kubernetes/apps/network/external-dns/app/secret.sops.yaml`                                        | DNS provider credentials.           |
| observability | grafana operator      | `kubernetes/apps/observability/grafana/operator/secret.sops.yaml`                                  | App-specific credentials.           |
| observability | grafana operator      | `kubernetes/apps/observability/grafana/operator/secret-oidc.sops.yaml`                             | OIDC client credentials.            |
| observability | kube-prometheus-stack | `kubernetes/apps/observability/kube-prometheus-stack/app/secret-additionalScrapeConfigs.sops.yaml` | Additional scrape configs.          |
| observability | kube-prometheus-stack | `kubernetes/apps/observability/kube-prometheus-stack/app/secret-alertmgrNotifiers.sops.yaml`       | Alertmanager notifiers.             |
| observability | nut-exporter          | `kubernetes/apps/observability/nut-exporter/app/secret.sops.yaml`                                  | App-specific credentials.           |
| security      | authelia              | `kubernetes/apps/security/authelia/app/secret.sops.yaml`                                           | App-specific credentials.           |
| security      | lldap                 | `kubernetes/apps/security/lldap/app/secret.sops.yaml`                                              | Directory credentials.              |
| blog          | hugo                  | `kubernetes/apps/blog/hugo/app/secret.sops.yaml`                                                   | App-specific credentials.           |

Notes:

- Bootstrap SOPS files remain encrypted after cutover for bootstrap/Flux workflows.
- Namespace inventories should drive `ExternalSecret` mappings during Phase 3.

## Phase 1: GitOps foundation in `kubernetes/apps/external-secrets`

Status checklist:

- [x] Deploy ESO via `external-secrets-operator` Flux Kustomization.
- [x] Deploy 1Password Connect + `ClusterSecretStore/onepassword` via `onepassword` Flux Kustomization.
- [x] Configure shared `ClusterExternalSecret` for `cluster-secrets` fan-out.
- [x] Provide example `ExternalSecret` and `ClusterExternalSecret` manifests.

### Phase 1 outputs (current repository state)

- Namespace + app root kustomization: `kubernetes/apps/external-secrets/`.
- ESO app: `kubernetes/apps/external-secrets/external-secrets-operator/`.
- 1Password app: `kubernetes/apps/external-secrets/onepassword/`.
- `ClusterSecretStore`: `onepassword`.
- Bootstrap secret expected in `external-secrets` namespace: `onepassword-secret` with keys:
  - `1password-credentials.json`
  - `token`

## Phase 2: Migration tooling and documentation

- [x] Inventory crawler: `scripts/onepassword/crawl.py`.
- [x] Push helper (SOPS -> 1Password via `op`): `scripts/onepassword/push.py`.
- [x] ExternalSecret generator: `scripts/onepassword/externalsecrets.py`.
- [x] Tooling guide: `docs/onepassword-eso-migration-tooling.md`.

## Phase 3: Namespace-by-namespace cutover

- [ ] For each namespace:
  - Create/adjust `ExternalSecret` resources mapping K8s keys to 1Password fields.
  - Update namespace app manifests to consume ESO-managed secrets.
  - Validate reconciliation (`ExternalSecret`/`ClusterSecretStore` Ready conditions).
  - Remove direct SOPS consumption once cutover is verified.

## Phase 4: Cleanup and legacy handling

- [ ] Keep minimal SOPS bootstrap only.
- [ ] Remove unused SOPS app secrets after successful namespace cutovers.
- [ ] Add monitoring/alerting for ESO sync errors and store readiness.

## Additional recommended milestones

- RBAC hardening: minimize ESO permissions and limit `ClusterExternalSecret` use where possible.
- Reliability: set/verify resource requests and disruption budgets for ESO + Connect.
- Observability: add dashboards/alerts for ESO reconciliation failures.
- Resilience drills: practice 1Password credential rotation and ESO recovery.

## Naming conventions (1Password + ESO)

- 1Password vault: `homelab` (use consistently for ESO and `op` references).
- `op` reference pattern: `op://homelab/<namespace>.<appname>/[section]/<field>`.
- 1Password item title: `{namespace}.{appname}` (example: `default.ghost`).
- Use `section` for grouping by purpose (for example `app`, `oidc`, `db`) when needed.
- Separator preference between namespace and app name: `.`, then `_`, then `-`.
- ESO's 1Password provider matches by field label and ignores section names, so field labels must be unique per item.
- Shared item titles: `shared.{purpose}`.
- Secret fields: `username`, `password`, `apiKey`, `token`, `certificate`, `privateKey`.
- Kubernetes Secret names: `app` or `app-<purpose>` in the app namespace.
- ExternalSecret resource names: `{namespace}-{app}-{source}` (example: `default-ghost`).
- ClusterSecretStore name: `onepassword`.
- `remoteRef.key` maps to item title; `remoteRef.property` maps to field label.

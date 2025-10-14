# Flux v2.7 Upgrade Readiness Review

## Release Highlights

Flux v2.7 promotes the Git, Kustomize, Source, OCI, and Notification APIs to GA and introduces the HelmRelease `helm.toolkit.fluxcd.io/v2` API. The release drops the legacy `v1beta` API versions and expects clusters to run the updated CRDs before reconciling managed resources. The `flux migrate` CLI command is the supported path for rewriting manifests that still reference pre-GA APIs, and Flux v2.7 controllers enforce the new schemas once the CRDs are installed.

## Repository State Against the Upgrade Checklist

- **Flux manifests pinned to v2.7.2** – `kubernetes/flux/config/flux.yaml` references `oci://ghcr.io/fluxcd/flux-manifests:v2.7.2`, ensuring the cluster pulls the v2.7 controller bundle and CRDs.【F:kubernetes/flux/config/flux.yaml†L1-L78】
- **GA APIs already in use** – sampled GitRepository, Kustomization, HelmRelease, and Notification manifests use the promoted GA API versions (`source.toolkit.fluxcd.io/v1`, `kustomize.toolkit.fluxcd.io/v1`, `helm.toolkit.fluxcd.io/v2`, and `notification.toolkit.fluxcd.io/v1`).【F:kubernetes/flux/config/cluster.yaml†L1-L36】【F:kubernetes/apps/blog/hugo/app/helmrelease.yaml†L1-L34】【F:kubernetes/apps/flux-system/addons/alerts/alertmanager/notification.yaml†L1-L26】
- **Bootstrap workflow installs CRDs server-side** – the Flux bootstrap Task applies the CRDs from the `bootstrap` Kustomization and then reconciles the repo definitions, aligning with the recommended upgrade flow.【F:.taskfiles/flux/taskfile.yaml†L17-L38】
- **No legacy API references found** – `rg "toolkit.fluxcd.io/v1beta"` returns no matches, indicating the repository has been fully migrated away from deprecated API versions.【48cf2a†L1-L2】

## Outstanding TODOs

1. **Update operator workstations to Flux CLI v2.7.x** – ensure every environment that runs `task flux:*` uses the matching CLI so that `flux check --pre` and `flux migrate` are available.
2. **Run `flux migrate` validation** – execute `flux migrate --path kubernetes --export --dry-run` and capture the diff to confirm there are no lingering pre-v2.7 manifests in private overlays.
3. **Plan the cluster rollout order** – schedule the CRD apply (`task :flux:bootstrap` stage) ahead of controller restarts to avoid reconciliation failures while the new schemas propagate.
4. **Re-run `flux check --pre` post-upgrade** – after applying the v2.7 bundle, execute `flux check --pre` to verify cluster prerequisites and confirm the controllers are healthy.
5. **Communicate HelmRelease API changes** – notify application owners that HelmRelease drift detection and OOM watch feature gates are enabled via patches so they can monitor for behaviour changes when Helm actions fail fast.

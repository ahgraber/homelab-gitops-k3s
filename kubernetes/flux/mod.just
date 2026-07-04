set quiet := true
set shell := ["bash", "-euo", "pipefail", "-c"]

flux_dir := source_directory()
root_dir := shell('git -C "' + flux_dir + '" rev-parse --show-toplevel')
kubernetes_dir := root_dir + "/kubernetes"
bootstrap_dir := root_dir + "/bootstrap"
scripts_dir := root_dir + "/scripts"
bootstrap_scripts_dir := scripts_dir + "/bootstrap"

[private]
default:
    just --list flux

[group("flux")]
[doc("Verify flux prerequisites")]
verify:
    flux check --pre

[group("flux")]
[doc("Bootstrap Flux into the cluster")]
bootstrap:
    test -f '{{ root_dir }}/kubeconfig'
    test -f '{{ root_dir }}/age.key'
    sops --decrypt '{{ bootstrap_dir }}/age-key.sops.yaml' >/dev/null
    op whoami >/dev/null
    '{{ bootstrap_scripts_dir }}/apply_namespaces.sh'
    '{{ bootstrap_scripts_dir }}/apply_sops_secrets.sh'
    '{{ bootstrap_scripts_dir }}/apply_bootstrap_resources.sh'
    '{{ bootstrap_scripts_dir }}/apply_crds.sh'
    '{{ bootstrap_scripts_dir }}/sync_hrs.sh'

[group("flux")]
[doc("Run flux-local tests against manifests")]
check path="":
    command -v flux-local >/dev/null
    flux-local test --path {{ if path == "" { kubernetes_dir } else { path } }}

[group("flux")]
[doc("Force Flux to pull and reconcile changes")]
reconcile:
    flux reconcile kustomization flux-cluster -n flux-system --with-source

[group("flux")]
[doc("Apply a local Flux Kustomization for a cluster app")]
apply-ks path ks ns="flux-system":
    existing=$(flux --namespace {{ ns }} get kustomizations {{ ks }} 2>&1 || true); \
    dry_run=""; \
    [[ "$existing" == *"not found"* ]] && dry_run="--dry-run"; \
    flux build ks {{ ks }} --namespace {{ ns }} --kustomization-file '{{ kubernetes_dir }}/apps/{{ path }}/ks.yaml' --path '{{ kubernetes_dir }}/apps/{{ path }}' $dry_run | \
      kubectl apply --server-side --field-manager=kustomize-controller -f -

[group("flux")]
[doc("Suspend all Flux kustomizations")]
suspend-ks:
    flux suspend kustomization --all

[group("flux")]
[doc("Resume all Flux kustomizations")]
resume-ks:
    flux resume kustomization --all

[group("flux")]
[doc("Suspend all Flux helmreleases")]
suspend-hr:
    kubectl get helmreleases -A --no-headers | while read -r ns name _; do \
      flux suspend helmrelease "$name" -n "$ns"; \
    done

[group("flux")]
[doc("Resume all Flux helmreleases")]
resume-hr:
    kubectl get helmreleases -A --no-headers | while read -r ns name _; do \
      flux resume helmrelease "$name" -n "$ns"; \
    done

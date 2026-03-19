set quiet := true
set shell := ["bash", "-euo", "pipefail", "-c"]

kubernetes_dir := source_directory()
root_dir := shell('git -C "' + kubernetes_dir + '" rev-parse --show-toplevel')
bootstrap_dir := root_dir + "/bootstrap"
scripts_dir := root_dir + "/scripts"
bootstrap_scripts_dir := scripts_dir + "/bootstrap"
volsync_scripts_dir := kubernetes_dir + "/apps/volsync-system/scripts"
volsync_templates_dir := volsync_scripts_dir + "/templates"

[private]
default:
    just --list kube

# ── Cluster ────────────────────────────────────────────────────────

[group("cluster")]
[doc("Install k3s via ansible")]
install:
    just ansible playbook k3s-install kubernetes --become

[group("cluster")]
[doc("Stop k3s via ansible")]
stop:
    just ansible playbook k3s-stop kubernetes --become

[group("cluster")]
[doc("Destroy k3s via ansible")]
nuke:
    just ansible playbook k3s-nuke kubernetes --become

[group("cluster")]
[doc("Download kubeconfig from a remote k3s controller")]
kubeconfig host="optiplex0" user="nrl":
    : "${KUBE_VIP_ADDR:?Set KUBE_VIP_ADDR in your environment}"
    scp "{{ user }}@{{ host }}:/etc/rancher/k3s/k3s.yaml" '{{ root_dir }}/kubeconfig'
    sed -i "s/127.0.0.1/$KUBE_VIP_ADDR/g" '{{ root_dir }}/kubeconfig'
    chmod go-r '{{ root_dir }}/kubeconfig'

[group("cluster")]
[doc("Validate manifests with kubeconform")]
kubeconform:
    bash '{{ scripts_dir }}/kubeconform.sh' '{{ kubernetes_dir }}'

[group("cluster")]
[doc("Drain a node")]
drain node:
    kubectl drain {{ node }} --delete-emptydir-data --ignore-daemonsets --force

[group("cluster")]
[doc("Uncordon a node")]
uncordon node:
    kubectl uncordon {{ node }}

[group("cluster")]
[doc("Gather common resources across the cluster")]
resources *args:
    for r in nodes gitrepositories kustomizations helmrepositories helmreleases certificates certificaterequests ingresses pods; do \
      kubectl get "$r" {{ if args == '' { "-A" } else { args } }}; \
    done

# ── Flux ───────────────────────────────────────────────────────────

[group("flux")]
[doc("Verify flux prerequisites")]
verify:
    flux check --pre

[group("flux")]
[doc("Bootstrap Flux into the cluster")]
bootstrap:
    test -f '{{ root_dir }}/kubeconfig'
    test -f '{{ root_dir }}/age.key'
    test -f '{{ bootstrap_dir }}/github-deploy-key.sops.yaml'
    sops --decrypt '{{ bootstrap_dir }}/age-key.sops.yaml' >/dev/null
    sops --decrypt '{{ bootstrap_dir }}/github-deploy-key.sops.yaml' >/dev/null
    '{{ bootstrap_scripts_dir }}/apply_namespaces.sh'
    '{{ bootstrap_scripts_dir }}/apply_sops_secrets.sh'
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

# ── Database (CNPG) ───────────────────────────────────────────────

[group("db")]
[doc("Hibernate a CNPG database")]
db-hibernate cnpg ns="default":
    kubectl annotate cluster {{ cnpg }} -n {{ ns }} --overwrite cnpg.io/hibernation=on

[group("db")]
[doc("Hibernate all CNPG databases")]
db-hibernate-all:
    kubectl get cluster --all-namespaces --no-headers | while read -r ns name _; do \
      kubectl annotate cluster "$name" -n "$ns" --overwrite cnpg.io/hibernation=on; \
    done

[group("db")]
[doc("Resume a CNPG database")]
db-resume cnpg ns="default":
    kubectl annotate cluster {{ cnpg }} -n {{ ns }} cnpg.io/hibernation-

[group("db")]
[doc("Resume all CNPG databases")]
db-resume-all:
    kubectl get cluster --all-namespaces --no-headers | while read -r ns name _; do \
      kubectl annotate cluster "$name" -n "$ns" cnpg.io/hibernation-; \
    done

# ── VolSync ───────────────────────────────────────────────────────

[group("volsync")]
[doc("Calculate relative path from one file to volsync components")]
relpath start end="./kubernetes/components/volsync":
    test -f {{ start }}
    test -d {{ end }}
    realpath --relative-to="$(dirname {{ start }})" "{{ end }}"

[group("volsync")]
[doc("List restic snapshots for a ReplicationSource")]
vs-list app ns="default":
    ts=$(date +%H%M%S); \
    export app='{{ app }}' ns='{{ ns }}' ts="$ts"; \
    envsubst < '{{ volsync_templates_dir }}/ListJob.tmpl.yaml' | kubectl apply -f -; \
    bash '{{ volsync_scripts_dir }}/wait-for-job.sh' "list-{{ app }}-$ts" '{{ ns }}'; \
    kubectl -n '{{ ns }}' wait job/list-{{ app }}-$ts --for condition=complete --timeout=1m; \
    kubectl -n '{{ ns }}' logs job/list-{{ app }}-$ts --container list; \
    kubectl -n '{{ ns }}' delete job list-{{ app }}-$ts

[group("volsync")]
[doc("Unlock restic repository for a ReplicationSource")]
vs-unlock app ns="default":
    ts=$(date +%H%M%S); \
    export app='{{ app }}' ns='{{ ns }}' ts="$ts"; \
    envsubst < '{{ volsync_templates_dir }}/UnlockJob.tmpl.yaml' | kubectl apply -f -; \
    bash '{{ volsync_scripts_dir }}/wait-for-job.sh' "unlock-{{ app }}-$ts" '{{ ns }}'; \
    kubectl -n '{{ ns }}' wait job/unlock-{{ app }}-$ts --for condition=complete --timeout=1m; \
    kubectl -n '{{ ns }}' logs job/unlock-{{ app }}-$ts --container unlock; \
    kubectl -n '{{ ns }}' delete job unlock-{{ app }}-$ts

[group("volsync")]
[doc("Trigger a restic ReplicationSource snapshot")]
vs-snapshot app ns="default":
    kubectl -n '{{ ns }}' get replicationsources {{ app }} >/dev/null
    kubectl -n '{{ ns }}' patch replicationsources {{ app }} --type merge \
      -p '{"spec":{"trigger":{"manual":"'"$(date +%H%M%S)"'"}}}'
    bash '{{ volsync_scripts_dir }}/wait-for-job.sh' volsync-src-{{ app }} '{{ ns }}'
    kubectl -n '{{ ns }}' wait job/volsync-src-{{ app }} --for condition=complete --timeout=120m

[group("volsync")]
[doc("Restore a ReplicationSource from a restic snapshot")]
vs-restore app ns="default" previous="2":
    bash '{{ volsync_scripts_dir }}/restore.sh' '{{ app }}' '{{ ns }}' '{{ previous }}'

# ── Debug ─────────────────────────────────────────────────────────

[group("debug")]
[doc("Browse PersistentVolumeClaim contents")]
browse-pvc app claim ns="default":
    ks=$(kubectl -n {{ ns }} get replicationsource {{ app }} -o jsonpath='{.metadata.labels.kustomize\.toolkit\.fluxcd\.io/name}'); \
    app_name=$(kubectl -n {{ ns }} get persistentvolumeclaim {{ claim }} -o jsonpath='{.metadata.labels.app\.kubernetes\.io/name}'); \
    if kubectl -n {{ ns }} get deployment.apps/$app_name >/dev/null 2>&1; then controller="deployment.apps/$app_name"; else controller="statefulset.apps/$app_name"; fi; \
    flux -n flux-system suspend kustomization "$ks"; \
    flux -n {{ ns }} suspend helmrelease {{ app }}; \
    kubectl -n {{ ns }} scale "$controller" --replicas 0; \
    kubectl -n {{ ns }} wait pod --for delete --selector='app.kubernetes.io/name={{ app }}' --timeout=2m; \
    kubectl browse-pvc --namespace {{ ns }} {{ claim }}; \
    flux -n {{ ns }} resume helmrelease {{ app }}; \
    flux -n flux-system resume kustomization "$ks"

[group("debug")]
[doc("Deploy local kustomization for testing")]
ks-deploy ks_path:
    cluster_secrets='{{ root_dir }}/kubernetes/flux/vars/cluster-secrets.sops.yaml'; \
    custom_secrets='{{ root_dir }}/kubernetes/flux/vars/custom-secrets.sops.yaml'; \
    cluster_config='{{ root_dir }}/kubernetes/flux/vars/cluster-settings.yaml'; \
    custom_config='{{ root_dir }}/kubernetes/flux/vars/custom-settings.yaml'; \
    while read -r line; do [[ "$line" = \#* ]] && continue; declare -x "${line}"; done < <(sops -d "$cluster_secrets" | yq eval '.stringData' - | sed 's/: /=/g'); \
    while read -r line; do [[ "$line" = \#* ]] && continue; declare -x "${line}"; done < <(sops -d "$custom_secrets" | yq eval '.stringData' - | sed 's/: /=/g'); \
    while read -r line; do [[ "$line" = \#* ]] && continue; declare -x "${line}"; done < <(yq eval '.data' "$cluster_config" | sed 's/: /=/g'); \
    while read -r line; do [[ "$line" = \#* ]] && continue; declare -x "${line}"; done < <(yq eval '.data' "$custom_config" | sed 's/: /=/g'); \
    kustomize build --load-restrictor=LoadRestrictionsNone "{{ ks_path }}" | envsubst | kubectl apply --server-side -f -

[group("debug")]
[doc("Revert local kustomization testing deployment")]
ks-undeploy ks_path:
    cluster_secrets='{{ root_dir }}/kubernetes/flux/vars/cluster-secrets.sops.yaml'; \
    cluster_config='{{ root_dir }}/kubernetes/flux/vars/cluster-settings.yaml'; \
    while read -r line; do [[ "$line" = \#* ]] && continue; declare -x "${line}"; done < <(sops -d "$cluster_secrets" | yq eval '.stringData' - | sed 's/: /=/g'); \
    while read -r line; do [[ "$line" = \#* ]] && continue; declare -x "${line}"; done < <(yq eval '.data' "$cluster_config" | sed 's/: /=/g'); \
    kustomize build --load-restrictor=LoadRestrictionsNone "{{ ks_path }}" | envsubst | kubectl delete -f -

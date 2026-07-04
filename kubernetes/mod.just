set quiet := true
set shell := ["bash", "-euo", "pipefail", "-c"]

kubernetes_dir := source_directory()
root_dir := shell('git -C "' + kubernetes_dir + '" rev-parse --show-toplevel')
scripts_dir := root_dir + "/scripts"

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
[doc("Gather common resources across the cluster (args: -n NAMESPACE; default: -A)")]
resources *args:
    for r in nodes gitrepositories kustomizations helmrepositories helmreleases certificates certificaterequests ingresses pods; do \
      kubectl get "$r" {{ if args == '' { "-A" } else { args } }}; \
    done

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

#!/usr/bin/env zsh
# shellcheck disable=SC1071

debug_hr="nextcloud"
debug_ns="nextcloud"
flux suspend kustomization core
flux suspend kustomization apps && sleep 10
flux delete hr "${debug_hr}" -n "${debug_ns}" -s && sleep 30

declare -a pvcs=($(kubectl get pvc -n "${debug_ns}" --no-headers | awk '{print $1}'))
declare -a pvs=($(kubectl get pvc -n "${debug_ns}" --no-headers | awk '{print $3}'))
for pvc in "${pvcs[@]}"; do kubectl delete pvc "${pvc}" -n "${debug_ns}"; done
for pv in "${pvs[@]}"; do kubectl delete pv "${pv}"; done
unset pvcs
unset pvs

kubectl delete ns "${debug_ns}" && sleep 30
function ns_cleanup {
  declare -a terminating=($(kubectl get ns -o json | jq '.items[] | select(.status.phase=="Terminating") | (.metadata.name)' | xargs -n1))
  for ns in "${terminating[@]}"; do
    echo "$ns"
    # kubectl get ns "$ns"  -o json | jq '.spec.finalizers = []' | kubectl replace --raw "/api/v1/namespaces/$ns/finalize" -f -
    kubectl patch ns "${ns}" -p '{"metadata":{"finalizers":null}}'
  done
  unset terminating
}
ns_cleanup

bash ./cluster/core/democratic-csi/cleanup.sh

flux resume kustomization core && flux reconcile kustomization core
flux resume kustomization apps && flux reconcile kustomization apps
flux-update

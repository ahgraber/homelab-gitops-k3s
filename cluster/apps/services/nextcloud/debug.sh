#!/bin/zsh

flux suspend kustomization core
flux suspend kustomization apps && sleep 10
flux delete hr nextcloud -n nextcloud -s && sleep 30

declare -a pvcs=($(kubectl get pvc -n nextcloud --no-headers | awk '{print $1}'))
declare -a pvs=($(kubectl get pvc -n nextcloud --no-headers | awk '{print $3}'))
for pvc in "${pvcs[@]}"; do kubectl delete pvc "$pvc" -n nextcloud; done;
for pv in "${pvs[@]}"; do kubectl delete pv "$pv"; done;
unset pvcs
unset pvs

kubectl delete ns nextcloud && sleep 30
function ns_cleanup {
  declare -a terminating=( $(kubectl get ns -o json | jq '.items[] | select(.status.phase=="Terminating") | (.metadata.name)' | xargs -n1) )
  for ns in "${terminating[@]}"; do
    echo "$ns"
    kubectl get ns "$ns"  -o json | jq '.spec.finalizers = []' | kubectl replace --raw "/api/v1/namespaces/$ns/finalize" -f -
  done
  unset terminating
}
ns_cleanup

bash ./cluster/core/democratic-csi/cleanup.sh

flux resume kustomization core && flux reconcile kustomization core
flux resume kustomization apps && flux reconcile kustomization apps
flux-update

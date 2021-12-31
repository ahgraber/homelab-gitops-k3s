# Rancher

Rancher is an open source container management platform built for organizations that deploy containers in production.
Rancher makes it easy to run Kubernetes everywhere, meet IT requirements, and empower DevOps teams.

> Currently disabled on homelab because init process does not jive with Flux.
> May be able to reconcile by running Rancher in a separate management cluster (via Helm) or
> on separate device (pi?) via Docker

## Setup

```sh
# kubectl get secret -n cattle-system bootstrap-secret -o yaml > ./cluster/apps/monitoring/rancher/boostrap-secret.yaml
kubectl get secret --namespace cattle-system bootstrap-secret -o go-template='{{.data.bootstrapPassword|base64decode}}{{"\n"}}'
```

```sh
kubectl get secret --namespace cattle-system bootstrap-secret -o go-template='{{.metadata.uid}}{{"\n"}}'
kubectl get secret --namespace cattle-system bootstrap-secret -o go-template='{{.metadata.annotations}}{{"\n"}}'
```

> IMPORTANT!  Add `.gitignore` to local folder to ensure secret is not shared

## Teardown

1. Delete namespaces

2. Delete CRDs by group

   ```zsh
   function crd_cleanup {
     groupname=$1
     search="kubectl get crd -o json \
       | jq '.items[] | select(.spec.group=="\"${groupname}\"") | (.metadata.name)' | xargs -n1"
     # echo $search
     # bash -c "$search"
     declare -a to_clean=( $(bash -c $search) )
     for crd in "${to_clean[@]}"; do
       echo "$crd"
       kubectl delete crd "$crd"
       # -o json | jq '.spec.finalizers = []' | kubectl replace --raw "/api/v1/namespaces/$ns/finalize" -f -
       kubectl patch crd "$crd" -p '{"metadata":{"finalizers":null}}'
     done
   }
   crd_cleanup "catalog.cattle.io"
   crd_cleanup "cluster.x-k8s.io.cattle.io"
   crd_cleanup "fleet.cattle.io"
   crd_cleanup "gitjob.cattle.io"
   crd_cleanup "management.cattle.io"
   crd_cleanup "project.cattle.io"
   crd_cleanup "provisioning.cattle.io"
   crd_cleanup "rke.cattle.io"
   crd_cleanup "rke-machine.cattle.io"
   crd_cleanup "ui.cattle.io"
   ```

3. Clean up namespaces

   ```zsh
   function ns_cleanup {
     declare -a terminating=( $(kubectl get ns -o json \
       | jq '.items[] | select(.status.phase=="Terminating") | (.metadata.name)' \
       | xargs -n1) )
     for ns in "${terminating[@]}"; do
       echo "$ns"
       # kubectl get ns "$ns"  -o json \
       #   | jq '.spec.finalizers = []' | kubectl replace --raw "/api/v1/namespaces/$ns/finalize" -f -
       kubectl patch ns "$ns" -p '{"metadata":{"finalizers":null}}'
     done
     unset terminating
   }
   ns_cleanup
   ```

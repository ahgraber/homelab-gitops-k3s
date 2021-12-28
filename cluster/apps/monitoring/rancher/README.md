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

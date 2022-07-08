#!/usr/bin/env bash

USER="admin"
kubectl create secret generic -n postgres stackgres-secret --dry-run=client -o json \
  --from-literal=k8sUsername="${USER}" \
  --from-literal=password="$(echo -n "${USER}${SECRET_DEFAULT_PWD}" | sha256sum | awk '{ print $1 }')" \
  --from-literal=clearPassword="${SECRET_DEFAULT_PWD}" \
| jq '.metadata.labels |= {"api.stackgres.io/auth":"user"}' \
| yq -o yaml --prettyPrint - \
>! ./cluster/apps/data/databases/stackgres/secret-stackgres.sops.yaml

unset USER

sops --encrypt --in-place ./cluster/apps/data/databases/stackgres/secret-stackgres.sops.yaml

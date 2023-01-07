#!/usr/bin/env bash

echo "If prompted to delete, respond true/false"

controllers=()
while IFS='' read -r line; do controllers+=("$line"); done < \
  <(kubectl get po -n democratic-csi | grep controller | awk '{ print $1 }')
for ctrl in "${controllers[@]}"; do
  kubectl -n democratic-csi exec -it "$ctrl" --container=csi-driver -- bash -c ./bin/k8s-csi-cleaner
done

#! /usr/bin/env bash

# Enable case-insensitive pattern matching
shopt -s nocasematch

patch_cephclusters () {
  mapfile -t -O "${#instances[@]}" instances < <( \
    kubectl get cephcluster -A \
      -o jsonpath='{range .items[*]}{.kind}{" "}{.metadata.name}{" -n "}{.metadata.namespace}{"\n"}{end}' \
  )

  for instance in "${instances[@]}"; do
    echo "Removing ${kind} ${instance}..."
    # split instance by space into array
    IFS=' ' read -ra _instance <<< "${instance}"
    # patch cleanup policy
    kubectl patch "${_instance[@]}" \
      --type merge -p '{"spec":{"cleanupPolicy":{"confirmation":"yes-really-destroy-data" }}}'
  done;
}

delete_resource () {
  kind="$1"

  unset instances
  mapfile -t -O "${#instances[@]}" instances < <( \
    kubectl get "${kind}" -A \
      -o jsonpath='{range .items[*]}{.kind}{" "}{.metadata.name}{" -n "}{.metadata.namespace}{"\n"}{end}' \
  )

  for instance in "${instances[@]}"; do
    echo "Deleting ${instance}"
    # split instance by space into array
    IFS=' ' read -ra _instance <<< "${instance}"
    # delete
    kubectl delete "${_instance[@]}"
  done;
}

delete_CRs () {
  # get all CR kinds associated with rook-ceph
  mapfile -t customresources < <(kubectl api-resources | grep ceph.rook.io | awk '{ print $1 }')

  # get all instances of these CRs
  for kind in "${customresources[@]}"; do
    # handle cephcluster separately
    if [[ "${kind}" =~ "cephcluster" ]]; then
      : # pass
    else
      echo "Removing ${kind} instances..."
      delete_resource "${kind}"
    fi;
  done;
}

delete_helmreleases () {
  mapfile -t -O "${#helmreleases[@]}" helmreleases < <( \
    kubectl get helmreleases -n rook-ceph \
      -o jsonpath='{range .items[*]}{.kind}{" "}{.metadata.name}{" -n "}{.metadata.namespace}{"\n"}{end}'
  )

  echo "Removing rook-ceph helmreleases..."
  for helmrelease in "${helmreleases[@]}"; do
    # split instance by space into array
    IFS=' ' read -ra _helmrelease <<< "${helmrelease}"
    kubectl delete helmrelease "${_helmrelease[@]}"
  done;
}

delete_storageclasses () {
  mapfile -t -O "${#storageclasses[@]}" storageclasses < <( \
    kubectl get storageclass -A \
      --selector helm.toolkit.fluxcd.io/namespace=rook-ceph \
      -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' \
  )

  echo "Removing rook-ceph storage classes..."
  for storageclass in "${storageclasses[@]}"; do
    kubectl delete storageclass "${storageclass}"
  done;
}

delete_crds () {
  mapfile -t crds < <(kubectl get customresourcedefinition | grep ceph.rook.io | awk '{ print $1 }')

  echo "Removing rook-ceph custom resource definitions..."
  for crd in "${crds[@]}"; do
    kubectl delete customresourcedefinition "${crd}"
  done;
}

delete_ns () {
  kubectl delete namespace rook-ceph
}
#--------------------------------------------------
echo "Removing rook-ceph..."

patch_cephclusters
delete_CRs
delete_resource "cephcluster"
delete_helmreleases
delete_storageclasses
delete_crds
delete_ns

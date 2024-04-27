#! /usr/bin/env bash

# storageclasses
get_storageclasses () {
  kubectl get storageclass -A \
    --selector helm.toolkit.fluxcd.io/namespace=rook-ceph \
    -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}'
}

get_pvcs_using_storageclass () {
  # get consumer pvcs associated with the provided storageclass
  storageclass="$1"

  kubectl get pvc -A \
    -o jsonpath="{range .items[?(@.spec.storageClassName=='${storageclass}')]}{.metadata.name}{' -n '}{.metadata.namespace}{'\n'}{end}"
}

get_apps_consuming_pvc () {
  pvc="$1"
  # split controller by space into array
  IFS=' ' read -ra _pvc <<< "${pvc}"
  kubectl get persistentvolumeclaim "${_pvc[@]}" \
    -o jsonpath="{.metadata.labels.app\.kubernetes\.io/name}"
}

scaledown_app () {
  app="$1"

  mapfile -t controllers < <(kubectl get deployment,statefulset -A \
    --selector app.kubernetes.io/name="${app}" \
    -o jsonpath='{range .items[*]}{.kind}{" "}{.metadata.name}{" -n "}{.metadata.namespace}{"\n"}{end}'
  )

  for controller in "${controllers[@]}"; do
    # split controller by space into array
    IFS=' ' read -ra _controller <<< "${controller}"
    # 'controller' --> '<type> <name> -n <namespace>'
    kubectl scale "${_controller[@]}" --replicas 0
  done;
  kubectl wait pod -A --for delete --selector="app.kubernetes.io/name='${app}'" --timeout=2m
  echo "Scaled ${app} to 0."
}

#--------------------------------------------------
echo "Identifying consumer applications..."

# get_storageclasses to array 'storageclasses'
mapfile -t -O "${#storageclasses[@]}" storageclasses < <(get_storageclasses)

# get pvcs consuming each storageclass
for storageclass in "${storageclasses[@]}"; do
  mapfile -t -O "${#pvcs[@]}" pvcs < <(get_pvcs_using_storageclass "${storageclass}")
done

# get apps associated with each pvc
for pvc in "${pvcs[@]}"; do
  mapfile -t -O "${#apps[@]}" apps < <(get_apps_consuming_pvc "${pvc}")
done

echo "Scaling down consumers..."
# scale down apps
for app in "${apps[@]}"; do
  scaledown_app "${app}"
done;
echo "Done."

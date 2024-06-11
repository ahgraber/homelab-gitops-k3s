#! /usr/bin/env bash

scaledown_rook_ceph () {

mapfile -t controllers < <(kubectl get deployment,statefulset -n rook-ceph \
    -o jsonpath='{range .items[*]}{.kind}{" "}{.metadata.name}{" -n "}{.metadata.namespace}{" "}{.metadata.labels.app}{"\n"}{end}'
)

for controller in "${controllers[@]}"; do
    # split controller by space into array
    IFS=' ' read -ra _controller <<< "${controller}"
    # 'controller' --> '<type> <name> -n <namespace>'

    # get appname for log
    app="$(kubectl get "${_controller[@]}" -o jsonpath='{.metadata.labels.app}')"
    # scale down
    kubectl scale "${_controller[@]}" --replicas 1
    kubectl wait pod -A --for delete --selector="app=${app}" --timeout=2m
    echo "Scaled ${app}."
done;
}

#--------------------------------------------------
echo "Resuming rook-ceph..."
scaledown_rook_ceph
echo "Done."

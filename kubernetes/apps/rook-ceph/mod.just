set quiet := true
set shell := ["bash", "-euo", "pipefail", "-c"]

rook_dir := source_directory()
rook_scripts := rook_dir + "/scripts"

[private]
default:
    just --list rook

[doc("Open a shell in rook-ceph toolbox")]
toolbox:
    pod=$(kubectl get pod -l 'app=rook-ceph-tools' -n rook-ceph --no-headers -o custom-columns=':metadata.name' | head -1); \
    kubectl exec -it "$pod" -n rook-ceph -- bash

[doc("Copy the rook-ceph dashboard password to the clipboard")]
dash-pass:
    kubectl get secret rook-ceph-dashboard-password -n rook-ceph \
      -o jsonpath='{.data.password}' | base64 --decode | pbcopy
    echo "Password is in clipboard ready to paste!"

[doc("Find and optionally cleanup orphan RBD images (args: --mode dry-run|trash|rm, --pool, --yes)")]
rbd-orphan-cleanup *args:
    bash '{{ rook_scripts }}/rook-rbd-orphan-cleanup.sh' {{ args }}

[doc("Resume rook-ceph after halting")]
resume:
    just flux resume-ks
    flux resume helmrelease rook-ceph-operator -n rook-ceph
    flux resume helmrelease rook-ceph-cluster -n rook-ceph
    bash '{{ rook_scripts }}/resume-rook-ceph.sh'
    sleep 120
    just flux reconcile
    sleep 30
    just flux resume-hr

[doc("Scale down rook-ceph and dependents")]
down:
    just flux suspend-ks
    just flux suspend-hr
    bash '{{ rook_scripts }}/scaledown-consumers.sh'
    bash '{{ rook_scripts }}/scaledown-rook-ceph.sh'

[doc("Decommission rook-ceph")]
decommission:
    just rook down
    bash '{{ rook_scripts }}/remove-rook-ceph.sh'
    just rook zap

[doc("Run ansible playbook to clean and zap disks")]
zap:
    just ansible playbook ceph-cleanup kubernetes -- --become

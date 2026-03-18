set quiet := true
set shell := ["bash", "-euo", "pipefail", "-c"]

rook_dir := justfile_directory()
rook_scripts := rook_dir + "/scripts"
root_dir := rook_dir + "/../../.."

[private]
default:
    just --list rook

[doc("Open a shell in rook-ceph toolbox")]
toolbox:
    pod=$(kubectl get pod -l 'app=rook-ceph-tools' -n rook-ceph --no-headers -o custom-columns=':metadata.name' | head -1); \
    kubectl exec -it "$pod" -n rook-ceph -- bash

[doc("Find and optionally cleanup orphan RBD images")]
rbd-orphan-cleanup *args:
    bash '{{ root_dir }}/scripts/rook-rbd-orphan-cleanup.sh' {{ args }}

[doc("Resume rook-ceph after halting")]
resume:
    just kube resume-ks
    flux resume helmrelease rook-ceph-operator -n rook-ceph
    flux resume helmrelease rook-ceph-cluster -n rook-ceph
    bash '{{ rook_scripts }}/resume-rook-ceph.sh'
    sleep 120
    just kube reconcile
    sleep 30
    just kube resume-hr

[doc("Scale down rook-ceph and dependents")]
down:
    just kube suspend-ks
    just kube suspend-hr
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

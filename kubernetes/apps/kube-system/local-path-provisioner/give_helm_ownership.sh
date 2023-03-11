#!/usr/bin/env bash
# shellcheck disable=SC2155
export KUBECONFIG="$(git rev-parse --show-toplevel)/kubeconfig"
export meta_namespace='{"metadata": {"annotations": {"meta.helm.sh/release-namespace": "kube-system"}}}'
export meta_releasename='{"metadata": {"annotations": {"meta.helm.sh/release-name": "local-path-provisioner"}}}'
export managed_by='{"metadata": {"labels": {"app.kubernetes.io/managed-by": "Helm"}}}'

kubectl patch -n kube-system configmap local-path-config --type=merge -p "${meta_namespace}"
kubectl patch -n kube-system configmap local-path-config --type=merge -p "${meta_releasename}"
kubectl patch -n kube-system configmap local-path-config --type=merge -p "${managed_by}"

kubectl patch -n kube-system deployment local-path-provisioner --type=merge -p "${meta_namespace}"
kubectl patch -n kube-system deployment local-path-provisioner --type=merge -p "${meta_releasename}"
kubectl patch -n kube-system deployment local-path-provisioner --type=merge -p "${managed_by}"

# kubectl patch storageclass local-path --type=merge -p "${meta_namespace}"
# kubectl patch storageclass local-path --type=merge -p "${meta_releasename}"
# kubectl patch storageclass local-path --type=merge -p "${managed_by}"
kubectl storageclass local-path

unset meta_namespace
unset meta_releasename
unset managed_by

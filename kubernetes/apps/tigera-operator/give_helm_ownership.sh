#!/usr/bin/env bash
# shellcheck disable=SC2155
export KUBECONFIG="$(git rev-parse --show-toplevel)/kubeconfig"
export meta_namespace='{"metadata": {"annotations": {"meta.helm.sh/release-namespace": "tigera-operator"}}}'
export meta_name='{"metadata": {"annotations": {"meta.helm.sh/release-name": "tigera-operator"}}}'
export managed_by='{"metadata": {"labels": {"app.kubernetes.io/managed-by": "Helm"}}}'

# kubectl patch apiserver default --type=merge -p "${meta_namespace}"
# kubectl patch apiserver default --type=merge -p "${meta_name}"
# kubectl patch apiserver default --type=merge -p "${managed_by}"
kubectl patch installation default --type=merge -p "${meta_namespace}"
kubectl patch installation default --type=merge -p "${meta_name}"
kubectl patch installation default --type=merge -p "${managed_by}"
# kubectl patch podsecuritypolicy tigera-operator --type=merge -p "${meta_namespace}"
# kubectl patch podsecuritypolicy tigera-operator --type=merge -p "${meta_name}"
# kubectl patch podsecuritypolicy tigera-operator --type=merge -p "${managed_by}"
kubectl patch -n tigera-operator deployment tigera-operator --type=merge -p "${meta_namespace}"
kubectl patch -n tigera-operator deployment tigera-operator --type=merge -p "${meta_name}"
kubectl patch -n tigera-operator deployment tigera-operator --type=merge -p "${managed_by}"
kubectl patch -n tigera-operator serviceaccount tigera-operator --type=merge -p "${meta_namespace}"
kubectl patch -n tigera-operator serviceaccount tigera-operator --type=merge -p "${meta_name}"
kubectl patch -n tigera-operator serviceaccount tigera-operator --type=merge -p "${managed_by}"
kubectl patch clusterrole tigera-operator --type=merge -p "${meta_namespace}"
kubectl patch clusterrole tigera-operator --type=merge -p "${meta_name}"
kubectl patch clusterrole tigera-operator --type=merge -p "${managed_by}"
kubectl patch clusterrolebinding tigera-operator tigera-operator --type=merge -p "${meta_namespace}"
kubectl patch clusterrolebinding tigera-operator tigera-operator --type=merge -p "${meta_name}"
kubectl patch clusterrolebinding tigera-operator tigera-operator --type=merge -p "${managed_by}"

unset meta_namespace
unset meta_name
unset managed_by

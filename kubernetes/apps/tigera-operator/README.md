# [Tigera Operator](https://github.com/tigera/operator)

Kubernetes operator for installing Calico and Calico Enterprise

## Give Helm ownership

(Re)Install Operator over ansible-installed version to allow subsequent cluster updates

```sh
zsh ./kubernetes/apps/tigera-operator/give_helm_ownership.sh
```

[see also](https://github.com/onedr0p/flux-cluster-template/issues/321)

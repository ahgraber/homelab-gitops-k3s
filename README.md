# Template for deploying k3s backed by Flux

Deploy a single [k3s](https://k3s.io/) cluster, managed by the GitOps tool [Flux](https://toolkit.fluxcd.io/).
Cluster provisioned with [pxe, ansible, and/or terraform](https://github.com/ahgraber/homelab-infra).

This Git repository will be specifies the state of the cluster. In addition, with the help of the
[Flux SOPS integration](https://toolkit.fluxcd.io/guides/mozilla-sops/) GPG encrypted secrets can be
committed to this public repo.

_With inspiration from the k8s-at-home community, especially the [cluster template](https://github.com/k8s-at-home/template-cluster-k3s)_

## Overview

- [Introduction](https://ahgraber.github.io/homelab-gitops-k3s/#wave-introduction)
- [Repository structure](https://ahgraber.github.io/homelab-gitops-k3s#open_file_folder-repository-structure)
- [Prerequisites](https://ahgraber.github.io/homelab-gitops-k3s/1-prerequisites)
- [Install k3s](https://ahgraber.github.io/homelab-gitops-k3s/2-install_k3s_with_ansible)
- [GitOps with Flux](https://ahgraber.github.io/homelab-gitops-k3s/3-gitops_with_flux)

# Template for deploying k3s backed by Flux

Deploy a single [k3s](https://k3s.io/) cluster, managed by the GitOps tool [Flux](https://toolkit.fluxcd.io/).
Cluster provisioned with [pxe, ansible, and/or terraform](https://github.com/ahgraber/homelab-infra).

This Git repository will be specifies the state of the cluster. In addition, with the help of the
[Flux SOPS integration](https://toolkit.fluxcd.io/guides/mozilla-sops/) GPG encrypted secrets can be
committed to this public repo.

_With inspiration from the k8s-at-home community, especially the [cluster template](https://github.com/k8s-at-home/template-cluster-k3s)_

## Overview

<!-- no toc -->
- [👋 Introduction](#-introduction)
- [:open\_file\_folder:  Repository structure](#open_file_folder-repository-structure)
- [Prerequisites](./1-prerequisites.md)
- [Install k3s](./2-install_k3s_with_ansible.md)
- [GitOps with Flux](./3-gitops_with_flux.md)

## 👋 Introduction

The following components will be installed in your [k3s](https://k3s.io/) cluster by default. They
are only included to get a minimum viable cluster up and running. You are free to add / remove
components to your liking but anything outside the scope of the below components are not supported
by this template.

Feel free to read up on any of these technologies before you get started to be more familiar with
them.

- [flux](https://toolkit.fluxcd.io/) - GitOps operator for managing Kubernetes clusters from a Git repository
- [kube-vip](https://kube-vip.io/) - Load balancer for the Kubernetes control plane nodes
- [metallb](https://metallb.universe.tf/) - Load balancer for Kubernetes services
- [cert-manager](https://cert-manager.io/) - Operator to request SSL certificates and store them as Kubernetes resources
- [calico](https://www.tigera.io/project-calico/) - Container networking interface for inter pod and service networking
- [external-dns](https://github.com/kubernetes-sigs/external-dns) - Operator to publish DNS records to Cloudflare (or other providers) based on Kubernetes ingresses
- [k8s_gateway](https://github.com/ori-edge/k8s_gateway) - DNS resolver that provides local DNS to your Kubernetes ingresses

## :open_file_folder:&nbsp; Repository structure

The Git repository contains the following directories under `cluster` and are ordered below by how
Flux will apply them.

- **bootstrap** directory helps initialize Flux
- **flux** directory installs Flux and defines macro dependencies
- **charts** directory containing pointers to helm charts
- **config** directory with cluster secrets and settings
- **crds** directory containing custom resource definitions (CRDs) that need to exist globally in your
  cluster before anything else exists
- **core** directory (depends on **charts**, **config**, **crds**) are important infrastructure applications (grouped by
  namespace) that should never be pruned by Flux
- **monitoring** directory (depends on **charts**, **config**, **crds**) with monitoring applications
- **apps** directory (depends on **core**, **monitoring**) is where your common applications (grouped by namespace)
  could be placed, Flux will prune resources here if they are not tracked by Git anymore

```txt
cluster
├── apps
|   ├── flux-system
|   ├── monitoring
│   ├── networking
│   ├── security
│   ├── services
│   └── system
├── bootstrap
├── charts
├── config
├── core
│   ├──
|   ├── flux-system
|   ├── kube-system
|   ├── networking
|   |   ├── cert-manager
|   |   ├── kube-vip
│   |   ├── metallb-system
│   |   └── tigera-operator
│   └── storage
|       └── <storage classes>
├── crds
├── flux
└──monitoring
    ├── kube-prometheus-stack
    └── ...
```

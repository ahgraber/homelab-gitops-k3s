# Homelab cluster with k3s and Flux

This repo configures a single [k3s](https://k3s.io/) cluster, managed by the GitOps tool [Flux](https://toolkit.fluxcd.io/).
Cluster provisioned with [pxe, ansible, and/or terraform](https://github.com/ahgraber/homelab-infra).

_With inspiration from the k8s-at-home community, especially [onedr0p's cluster template](https://github.com/onedr0p/flux-cluster-template)_

## Overview

<!-- no toc -->
- [👋 Introduction](#-introduction)
- [📂 Repository structure](#-repository-structure)
- [📝 Prerequisites](./1-prerequisites.md)
- [📡 Install k3s](./2-install_k3s_with_ansible.md)
- [🤖 GitOps with Flux](./3-gitops_with_flux.md)

## 👋 Introduction

The following components are installed in the [k3s](https://k3s.io/) cluster by default.

- [flux](https://toolkit.fluxcd.io/) - GitOps operator for managing Kubernetes clusters from a Git repository
- [kube-vip](https://kube-vip.io/) - Load balancer for the Kubernetes control plane nodes
- [metallb](https://metallb.universe.tf/) - Load balancer for Kubernetes services
- [cert-manager](https://cert-manager.io/) - Operator to request SSL certificates and store them as Kubernetes resources
- [calico](https://www.tigera.io/project-calico/) - Container networking interface for inter pod and service networking
- [external-dns](https://github.com/kubernetes-sigs/external-dns) - Operator to publish DNS records to Cloudflare (or other providers) based on Kubernetes ingresses
- [k8s_gateway](https://github.com/ori-edge/k8s_gateway) - DNS resolver that provides local DNS to your Kubernetes ingresses

## 📂 Repository structure

The Git repository contains the following directories under `cluster` and are ordered below by how
Flux will apply them.

- **bootstrap** helps initialize Flux
- **flux** installs Flux, defines the cluster, and deploys cluster secrets and variables
- **apps** organizes all applications.  Applications are defined by a nested folder where the exterior
  folder contains a "fluxtomization" (kustomize.toolkit.fluxcd.io/v1beta2) that manages dependencies,
  and the inner folder contains a kustomization (kustomize.config.k8s.io/v1beta1) that deploys the manifests.

```txt
kubernetes
├── apps
|   ├── cluster-system - cluster management & internal applications
|   ├── flux-system - flux/gitops resources & applications
|   ├── kube-system - k8s system management
|   ├── monitoring
|   |   ├── grafana
|   |   ├── kube-prometheus-stack
│   |   ├── kubernetes-dashboard
│   |   └── ...
│   ├── networking
|   |   ├── cert-manager
|   |   ├── kube-vip
│   |   ├── metallb-system
│   |   ├── tigera-operator
│   |   ├── traefik
│   |   └── ...
│   ├── services - public services & applications
│   └── storage - storage providers
├── bootstrap
└── flux
    ├── config - cluster definition
    ├── repositories - source repositories (git, helm, OCI)
    └── vars - cluster secrets and variables
```

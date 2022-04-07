# Template for deploying k3s backed by Flux

Deploy a single [k3s](https://k3s.io/) cluster, managed by the GitOps tool [Flux](https://toolkit.fluxcd.io/).
Cluster provisioned with [pxe, ansible, and/or terraform](https://github.com/ahgraber/homelab-infra).

This Git repository will be specifies the state of the cluster. In addition, with the help of the
[Flux SOPS integration](https://toolkit.fluxcd.io/guides/mozilla-sops/) GPG encrypted secrets can be
committed to this public repo.

## With Inspiration from

- [onedr0p](https://github.com/onedr0p/home-cluster/)
- [bjw-s](https://github.com/bjw-s/k8s-gitops)
- [carpenike](https://github.com/carpenike/k8s-gitops/tree/master/cluster/apps/security)
- [billimek](https://github.com/billimek/k8s-gitops)

## Overview

- [Introduction](https://github.com/k8s-at-home/template-cluster-k3s#wave-introduction)
- [Prerequisites](./docs/1-prerequisites.md)
- [Repository structure](https://github.com/k8s-at-home/template-cluster-k3s#open_file_folder-repository-structure)
- [Install k3s](./docs/2-install_k3s_with_ansible.md) and [kube-vip](docs/2a-kube-vip.md)
- [GitOps with Flux](./docs/3-gitops_with_flux.md)

## :wave:&nbsp; Introduction

The following components are the foundation of the [k3s](https://k3s.io/) cluster.

- [flux](https://toolkit.fluxcd.io/)
- [calico](https://github.com/projectcalico/calico)
- [metallb](https://metallb.universe.tf/)
- [cert-manager](https://cert-manager.io/) with Cloudflare DNS challenge
- [system-upgrade-controller](https://github.com/rancher/system-upgrade-controller)

## :open_file_folder:&nbsp; Repository structure

The Git repository contains the following directories under `cluster` and are ordered below by how
Flux will apply them.

- **base** directory is the entrypoint to Flux
- **crds** directory contains custom resource definitions (CRDs) that need to exist globally in your
  cluster before anything else exists
- **core** directory (depends on **crds**) are important infrastructure applications (grouped by
  namespace) that should never be pruned by Flux
- **apps** directory (depends on **core**) is where your common applications (grouped by namespace)
  could be placed, Flux will prune resources here if they are not tracked by Git anymore

```txt
cluster
├── apps
│   ├── default
│   ├── networking
│   └── system-upgrade
├── base
│   └── flux-system
├── core
│   ├── cert-manager
│   ├── metallb-system
│   ├── namespaces
│   └── system-upgrade
└── crds
    └── cert-manager
```

### direnv

`direnv` is a great tool allowing a dynamic export of environment variables depending
on the current working directory.
See their [installation guide](https://direnv.net/docs/installation.html) and
don't forget to hook it into your shell!

### VSCode SOPS extension

[VSCode SOPS](https://marketplace.visualstudio.com/items?itemName=signageos.signageos-vscode-sops)
is a plugin for VSCode. It will automatically decrypt you SOPS secrets when
you click on the file in the editor and encrypt them when you save and exit the file.

### :robot:&nbsp; Automation

- [Renovate](https://www.whitesourcesoftware.com/free-developer-tools/renovate) is a very useful
  tool that when configured will start to create PRs in your Github repository when Docker images,
  Helm charts or anything else that can be tracked has a newer version. The configuration for
  renovate is located [here](./.github/renovate.json5).

- [system-upgrade-controller](https://github.com/rancher/system-upgrade-controller) will watch for
  new k3s releases and upgrade your nodes when new releases are found.

There's also a couple Github workflows included in this repository that help automate some processes.

- [Flux upgrade schedule](./.github/workflows/flux-schedule.yaml) - workflow to upgrade Flux.
- [Renovate schedule](./.github/workflows/renovate-schedule.yaml) - workflow to annotate
  `HelmRelease`'s which allows
  [Renovate](https://www.whitesourcesoftware.com/free-developer-tools/renovate) to track Helm chart
  versions.

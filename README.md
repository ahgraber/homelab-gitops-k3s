# Template for deploying k3s backed by Flux

Template for deploying a single [k3s](https://k3s.io/) cluster with [k3sup](https://github.com/alexellis/k3sup),
backed by [Flux](https://toolkit.fluxcd.io/) and [SOPS](https://toolkit.fluxcd.io/guides/mozilla-sops/).

The purpose here is to showcase how you can deploy an entire Kubernetes cluster
and show it off to the world using the
[GitOps](https://www.weave.works/blog/what-is-gitops-really) tool
[Flux](https://toolkit.fluxcd.io/).
When completed, your Git repository will be driving the state of your cluster.
In addition with the help of the [Flux SOPS integration](https://toolkit.fluxcd.io/guides/mozilla-sops/)
you'll be able to commit GPG encrypted secrets to your public repo.

## With Inspiration from

* [onedr0p](https://github.com/onedr0p/home-cluster/)
* [bjw-s](https://github.com/bjw-s/k8s-gitops)
* [carpenike](https://github.com/carpenike/k8s-gitops/tree/master/cluster/apps/security)
* [zacheryph](https://github.com/zacheryph/k8s-gitops)
* [billimek](https://github.com/billimek/k8s-gitops)
* [toboshii](https://github.com/toboshii/home-cluster)
* [budimanjojo](https://github.com/budimanjojo/home-cluster)

## Overview

* [Introduction](https://github.com/k8s-at-home/template-cluster-k3s#wave-introduction)
* [Prerequisites](./docs/1%20-%20prerequisites.md)
* [Repository structure](https://github.com/k8s-at-home/template-cluster-k3s#open_file_folder-repository-structure)
* [Install k3s](./docs/2%20-%20install%20k3s.md) and [kube-vip](docs/2a%20-%20kube-vip.md)
* [GitOps with Flux](./docs/3%20-%20gitops%20with%20flux.md)

## :wave:&nbsp; Introduction

The following components will be installed in your [k3s](https://k3s.io/)
cluster by default.
They are only included to get a minimum viable cluster up and running.
You are free to add / remove components to your liking but anything outside
the scope of the below components are not supported by this template.

Feel free to read up on any of these technologies before you get started to be
more familiar with them.

* [flannel](https://github.com/flannel-io/flannel)
* [flux](https://toolkit.fluxcd.io/)
* [metallb](https://metallb.universe.tf/)
* [cert-manager](https://cert-manager.io/) with Cloudflare DNS challenge
* [homer](https://github.com/bastienwirtz/homer)
* [system-upgrade-controller](https://github.com/rancher/system-upgrade-controller)

## :open_file_folder:&nbsp; Repository structure

The Git repository contains the following directories under `cluster`
and are ordered below by how Flux will apply them.

* **base** directory is the entrypoint to Flux
* **crds** directory contains custom resource definitions (CRDs)
  that need to exist globally in your cluster before anything else exists
* **core** directory (depends on **crds**) are important infrastructure
  applications (grouped by namespace) that should never be pruned by Flux
* **apps** directory (depends on **core**) is where your common applications
  (grouped by namespace) could be placed, Flux will prune resources here if
  they are not tracked by Git anymore

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

This is a great tool to export environment variables depending on what your
present working directory is, head over to their
[installation guide](https://direnv.net/docs/installation.html)
and don't forget to hook it into your shell!

When this is done you no longer have to use `--kubeconfig=./kubeconfig` in
your `kubectl`, `flux` or `helm` commands.

### VSCode SOPS extension

[VSCode SOPS](https://marketplace.visualstudio.com/items?itemName=signageos.signageos-vscode-sops)
is a neat little plugin for those using VSCode.
It will automatically decrypt you SOPS secrets when you click on the file in
the editor and encrypt them when you save  and exit the file.

### :robot:&nbsp; Automation

* [Renovate](https://www.whitesourcesoftware.com/free-developer-tools/renovate)
  is a very useful tool that when configured will start to create PRs in your
  Github repository when Docker images, Helm charts or anything else that
  can be tracked has a newer version. The configuration for renovate is
  located [here](./.github/renovate.json5).

* [system-upgrade-controller](https://github.com/rancher/system-upgrade-controller)
  will watch for new k3s releases and upgrade your nodes when new releases are
  found.

There's also a couple Github workflows included in this repository that
will help automate some processes.

* [Flux upgrade schedule](./.github/workflows/flux-schedule.yaml) - workflow to
  upgrade Flux.
* [Renovate schedule](./.github/workflows/renovate-schedule.yaml) - workflow to
  annotate `HelmRelease`'s which allows [Renovate](https://www.whitesourcesoftware.com/free-developer-tools/renovate)
  to track Helm chart versions.

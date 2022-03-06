# [node feature discovery](https://github.com/kubernetes-sigs/node-feature-discovery)

This software enables node feature discovery for Kubernetes.
It detects hardware features available on each node in a Kubernetes cluster,
and advertises those features using node labels.

NFD consists of three software components:

1. nfd-master
2. nfd-worker
3. nfd-topology-updater

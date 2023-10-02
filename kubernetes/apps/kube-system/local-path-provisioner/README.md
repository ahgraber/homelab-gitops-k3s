# [Local Path Provisioner](https://github.com/rancher/local-path-provisioner)

Dynamically provisioning persistent local storage with Kubernetes.

Local Path Provisioner provides a way for the Kubernetes users to utilize the local storage in each node.
Based on the user configuration, the Local Path Provisioner will create either
hostPath or local based persistent volume on the node automatically.
It utilizes the features introduced by Kubernetes Local Persistent Volume feature,
but makes it a simpler solution than the built-in local volume feature in Kubernetes.

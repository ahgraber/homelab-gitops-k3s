# Troubleshooting nodes

- Check node status

  ```sh
  kubectl --kubeconfig=${KUBECONFIG} get nodes -o wide
  kubectl --kubeconfig=${KUBECONFIG} describe node NODENAME
  ```

- Add or overwrite a taint (see [taints and tolerations](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/))

  ```sh
  # add/overwrite
  kubectl --kubeconfig=${KUBECONFIG} taint nodes NODENAME KEY=VALUE:NoSchedule
  # remove specific value taint
  kubectl --kubeconfig=${KUBECONFIG} taint nodes NODENAME KEY=VALUE:NoSchedule-
  # remove all taints from given key
  kubectl --kubeconfig=${KUBECONFIG} taint nodes NODENAME KEY-
  ```

  Example: Remove disk pressure taint

  ```sh
  kubectl --kubeconfig=${KUBECONFIG} taint nodes NODENAME node.kubernetes.io/disk-pressure-
  ```

# Troubleshooting nodes

- Check node status

  ```sh
  kubectl --kubeconfig=${KUBECONFIG} get nodes -o wide
  kubectl --kubeconfig=${KUBECONFIG} describe node NAME
  ```

- Remove disk pressure taint

  ```sh
  kubectl --kubeconfig=${KUBECONFIG} taint nodes {NODENAME} node.kubernetes.io/disk-pressure-
  ```
# Troubleshooting nodes

- Check node status

  ```sh
  kubectl --kubeconfig=${KUBECONFIG} get nodes -o wide
  kubectl --kubeconfig=${KUBECONFIG} describe node NODENAME
  ```

- Check node taints

  ```sh
  kubectl get nodes -o json | jq '.items[].spec.taints'
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

- Clear evicted pods

  ```sh
  kubectl get po --all-namespaces -o json | \
    jq  '.items[] | select(.status.reason!=null) | select(.status.reason | contains("Evicted")) |
    "kubectl delete po \(.metadata.name) -n \(.metadata.namespace)"' | xargs -n 1 bash -c
  ```

## Checking node logs (from node)

```sh
journalctl -u k3s -n 20
```

> If `journalctl -u k3s` has many "" entries, remove the offending pod volume
>
> ```sh
> sudo rm -rf /var/lib/kubelet/pods/<POD VOLUME ID>
> ```

## Check node configuration (from node)

* check k3s configuration:

  ```sh
  cat /etc/rancher/k3s/config.yaml
  ```

* Other important file locations:
  * `/var/lib/rancher/k3s`
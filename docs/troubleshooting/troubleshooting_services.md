# Troubleshooting services

## Debug HelmRelease

- Show the health of helm _releases_

  ```sh
  flux --kubeconfig=${KUBECONFIG} get helmrelease -A
  ```

- Force flux to reconcile a helm release:

  ```sh
  flux reconcile helmrelease traefik -n networking
  ```

- Debug a nonfunctional helm release

  ```sh
  # identify helm-controller name
  HELM_CTL=$(kubectl get pods -n flux-system | grep helm-controller | awk '{print $1}')
  # find last 20 logs for helmrelease name
  kubectl --kubeconfig=${KUBECONFIG} logs ${HELM_CTL} -n flux-system | grep traefik | tail -20
  # get flux logs
  flux logs --kind=HelmRelease --name=traefik -n networking --tail 20
  # check configured values
  helm get values traefik -n networking
  ```

- Show the health of your Helm _repositories_

  ```sh
  flux --kubeconfig=${KUBECONFIG} get sources helm -A
  ```

- Force flux to sync a helm repository:

  ```sh
  flux reconcile source helm traefik-charts -n flux-system
  ```

### Delete and reinstall errored helm deployments

- Delete helm deployment and `flux reconcile`

  ```sh
  helm delete traefik -n networking
  sleep 120 && flux reconcile hr traefik -n networking
  flux get hr traefik -n networking
  ```

- Delete helmrelease and reinstall via full app kustomization

  ```sh
  flux delete hr traefik -n networking -s
  sleep 120 && flux reconcile kustomization apps
  flux get hr traefik -n networking
  ```

## Debug namespaces

- Get all resources in a given namespace

  ```sh
  kubectl get all -n <namespace>
  ```

- Force delete namespace

  ```sh
  kubectl delete ns <namespace> --force
  ```

- Overwrite finalizers if namespace stuck `terminating`

  ```sh
  namespace=<namespace>
  kubectl get ns $namespace  -o json | jq '.spec.finalizers = []' | kubectl replace --raw "/api/v1/namespaces/$namespace/finalize" -f -
  ```

## Debug Pods

- Identify pods with

  ```sh
  kubectl --kubeconfig=${KUBECONFIG} get pods -o wide -A
  ```

- Get pod issues with

  ```sh
  kubectl --kubeconfig=${KUBECONFIG} describe pods <POD_NAME> -n <POD_NAMESPACE>
  ```

- Get specific pod logs with

  ```sh
  kubectl --kubeconfig=${KUBECONFIG} logs <POD_NAME> -n <POD_NAMESPACE>
  ```

- Get all logs pertaining to app with

  ```sh
  # kubectl --kubeconfig=${KUBECONFIG} logs -l app.kubernetes.io/name=<NAME> -n <POD_NAMESPACE>
  kubectl --kubeconfig=${KUBECONFIG} logs -l app.kubernetes.io/name=traefik -n networking
  ```

- Clear evicted pods

  ```sh
  kubectl get po --all-namespaces -o json | \
    jq  '.items[] | select(.status.reason!=null) | select(.status.reason | contains("Evicted")) |
    "kubectl delete po \(.metadata.name) -n \(.metadata.namespace)"' | xargs -n 1 bash -c
  ```

- Force delete stalled pods

```sh
kubectl delete pods <pod> --grace-period=0 --force
# if pod is stuck on `Unknown` state, run:
kubectl patch pod <pod> -p '{"metadata":{"finalizers":null}}'
```

- Remove disk pressure taint

  ```sh
  kubectl taint nodes {NODENAME} node.kubernetes.io/disk-pressure-
  ```

### Delete released PVs

```sh
kubectl get pv | grep "Released" | awk '{print $1}' | while read vol; do kubectl delete pv/${vol}; done
```

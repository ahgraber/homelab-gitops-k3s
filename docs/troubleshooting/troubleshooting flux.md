# Troubleshooting flux system

- Verify flux is running

  ```sh
  kubectl --kubeconfig=${KUBECONFIG} get pods -n flux-system
  ```

- Manually sync Flux with your Git repository

  ```sh
  flux --kubeconfig=${KUBECONFIG} reconcile source git flux-system
  ```

- Get status of objects managed by Flux

  ```sh
  # flux --kubeconfig=${KUBECONFIG} get all -A
  flux get sources git -A
  flux get sources helm -A
  flux get sources chart -A
  flux get helmrelease -A
  flux get kustomization -A
  ```

- Force flux to reconcile:

  ```sh
  flux reconcile helmrelease RELEASENAME -n NAMESPACE
  flux reconcile kustomization NAME
  flux reconcile source SOURCE NAME
  ```

- View kustomization logs

  ```sh
  flux logs --kind=HelmRelease
  flux logs --kind=Kustomization --name=apps

  ```

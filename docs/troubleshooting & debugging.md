# Troubleshooting & Debugging

## Verify Flux

```sh
kubectl --kubeconfig=${KUBECONFIG} get pods -n flux-system
```

## Verify ingress

Check `https://traefik.${BOOTSTRAP_DOMAIN}/dashboard`

Provide a dns override for `https://homer.${BOOTSTRAP_DOMAIN}` in your router
<!--
or update your hosts
file to verify the ingress controller is working.

```sh
echo "${BOOTSTRAP_METALLB_FRONTEND} ${BOOTSTRAP_DOMAIN} homer.${BOOTSTRAP_DOMAIN}" | sudo tee -a /etc/hosts
```
-->

Head over to your browser and you _should_ be able to access
`https://homer.${BOOTSTRAP_DOMAIN}`

## VSCode SOPS extension

[VSCode SOPS](https://marketplace.visualstudio.com/items?itemName=signageos.signageos-vscode-sops)
is a neat little plugin for those using VSCode.
It will automatically decrypt you SOPS secrets when you click on the file
in the editor and encrypt them when you save  and exit the file.

## :point_right:&nbsp; Debugging

### 1. Sync with repo

* Manually sync Flux with your Git repository

  ```sh
  flux --kubeconfig=${KUBECONFIG} reconcile source git flux-system
  ```

* Show the health of your main Flux `GitRepository`

  ```sh
  flux --kubeconfig=${KUBECONFIG} get sources git
  ```

### 2. Debug Kustomizations

* Show the health of kustomizations

  ```sh
  kubectl --kubeconfig=${KUBECONFIG} get kustomization -A
  ```

* Force flux to reconcile a kustomization:

  ```sh
  flux reconcile kustomization apps
  ```

* View kustomization logs

  ```sh
  flux logs --kind=Kustomization --name=apps
  ```

### 3. Debug Helm releases

* Show the health of helm _releases_

  ```sh
  flux --kubeconfig=${KUBECONFIG} get helmrelease -A
  ```

* Force flux to reconcile a helm release:

  ```sh
  flux reconcile helmrelease traefik -n networking
  ```

* Debug a nonfunctional helm release

  ```sh
  # identify helm-controller name
  HELM_CTL=$(kubectl get pods -n flux-system | grep helm-controller | awk '{print $1}')
  # find last 20 logs for helmrelease name
  kubectl --kubeconfig=${KUBECONFIG} logs ${HELM_CTL} -n flux-system | grep traefik | tail -20
  # get flux logs
  flux logs --kind=HelmRelease --name=traefik -n networking --tail 20
  ```

* Show the health of your Helm _repositories_

  ```sh
  flux --kubeconfig=${KUBECONFIG} get sources helm -A
  ```

* Force flux to sync a helm repository:

  ```sh
  flux reconcile source helm traefik-charts -n flux-system
  ```

#### Delete and reinstall errored helm deployments

* Delete helm deployment and `flux reconcile`

  ```sh
  helm delete traefik -n networking
  sleep 120 && flux reconcile hr traefik -n networking
  flux get hr traefik -n networking
  ```

* Delete helmrelease and reinstall via full app kustomization

  ```sh
  flux delete hr traefik -n networking
  sleep 120 && flux reconcile kustomization apps
  flux get hr traefik -n networking
  ```
# :small_blue_diamond:&nbsp; GitOps (with Flux)

:round_pushpin: Here we will be installing [flux](https://toolkit.fluxcd.io/)
after some quick bootstrap steps.

## 1. Verify Flux can be installed

```sh
flux --kubeconfig=$(pwd)/kubeconfig check --pre
# ► checking prerequisites
# ✔ kubectl 1.21.0 >=1.18.0-0
# ✔ Kubernetes 1.20.5+k3s1 >=1.16.0-0
# ✔ prerequisites checks passed
```

## 2. Pre-create the `flux-system` namespace

```sh
kubectl --kubeconfig=${KUBECONFIG} create namespace flux-system --dry-run=client -o yaml | kubectl --kubeconfig=./kubeconfig apply -f -
```

## 3. Add the Flux GPG key in-order for Flux to decrypt SOPS secrets

```sh
gpg --export-secret-keys --armor "${FLUX_KEY_FP}" |
kubectl --kubeconfig=${KUBECONFIG} create secret generic sops-gpg \
    --namespace=flux-system \
    --from-file=sops.asc=/dev/stdin
```

## 4. Export more environment variables for application configuration

> _Note: Exported variables go into `./tmpl/...`, where there are exported to settings and secrets in the next step_

**Edit before running or copying exports into .envrc**

```sh
cat << EOF >> .envrc

# The repo you created from this template
export BOOTSTRAP_GITHUB_REPOSITORY="https://github.com/ahgraber/homelab-gitops-k3s"
export GITHUB_USER="ahgraber"
export GITHUB_TOKEN="qwertyuiop123456789"
# Choose one of your domains or use a made up one
export BOOTSTRAP_DOMAIN="DOMAIN.COM"
# Cloudflare API token for DNS certification
export BOOTSTRAP_CLOUDFLARE_EMAIL="k8s-at-home@gmail.com"
export BOOTSTRAP_CLOUDFLARE_TOKEN="kpG6iyg3FS_du_8KRShdFuwfbwu3zMltbvmJV6cD"
# Pick a range of *UNUSED* IPs that are on the same network as your nodes
# Note: these cannot overlap with the kube-vip IP
export BOOTSTRAP_METALLB_LB_RANGE="10.42.42.200-10.42.42.242"
export BOOTSTRAP_METALLB_FRONTEND="10.42.42.42"
export BOOTSTRAP_METALLB_RANCHER="10.42.42.42"

# Generate hashed user/password for traefik basicauth
export TRAEFIK_BASICAUTH='$(htpasswd -nb <USERNAME> <PASSWORD> | openssl base64)'
EOF
```

## 5. Create required files based on ALL exported environment variables

> If additional customization is needed via variable exports, export variables,
create templates in `./tmpl`, and add to export code below
> If recreating secrets, may have to delete 'real' files outside of `./tmpl`
> `>!` allows replacing of files on zsh.  In other shells, may use `>`

```zsh
# reload all env variables
direnv allow .

# create SOPS hook for secret encryption
envsubst < ./tmpl/.sops.yaml >! ./.sops.yaml
# encrypt secrets
envsubst < ./tmpl/cluster-secrets.sops.yaml >! ./cluster/base/cluster-secrets.sops.yaml
envsubst < ./tmpl/cluster-settings.yaml >! ./cluster/base/cluster-settings.yaml
envsubst < ./tmpl/gotk-sync.yaml >! ./cluster/base/flux-system/gotk-sync.yaml
envsubst < ./tmpl/cert-manager-secret.sops.yaml >! ./cluster/core/cert-manager/secret.sops.yaml
envsubst < ./tmpl/traefik-middlewares-secret.sops.yaml >! ./cluster/apps/networking/traefik/middlewares/secret.sops.yaml
# add addl config/secrets
```

## 6. :mag:&nbsp; **Verify** all the above files have the correct information present

## 7. :closed_lock_with_key:&nbsp; Encrypt secrets with SOPS

> If additional customization is needed add new files to export code below

```sh
export GPG_TTY=$(tty)
sops --encrypt --in-place ./cluster/base/cluster-secrets.sops.yaml
sops --encrypt --in-place ./cluster/core/cert-manager/secret.sops.yaml
sops --encrypt --in-place ./cluster/apps/networking/traefik/middlewares/secret.sops.yaml
# add add'l secrets
```

:round_pushpin: Variables defined in `cluster-secrets.yaml` and
`cluster-settings.yaml` will be usable anywhere in your YAML manifests
under `./cluster`

## 8. :mag:&nbsp; **Verify** all the above files are **encrypted** with SOPS

## 9. Push your changes to git

```sh
git add -A
git commit -m "initial commit"
git push
```

## 10. Install Flux

* [ ] Generate a new Github Personal Access Token with all `repository` permissions and add/update .envrc
* [ ] Sync local repo with github
* [ ] Bootstrap flux integration:

<!-- ```sh
flux bootstrap github \
--owner="${GITHUB_USER}" \
--repository="${GITHUB_REPO}" \
--path=cluster/base \
--personal \
--private=true \
--token-auth \
--network-policy=false
```

_**Note**: When using k3s @onedr0p found that the network-policy flag has to be set to false, or Flux will not work_ -->

:round_pushpin: Due to race conditions with the Flux CRDs you will have to
*run the below command twice*. There should be no errors on this second run.

```sh
kubectl --kubeconfig=${KUBECONFIG} apply --kustomize=./cluster/base/flux-system
# namespace/flux-system configured
# customresourcedefinition.apiextensions.k8s.io/alerts.notification.toolkit.fluxcd.io created
# customresourcedefinition.apiextensions.k8s.io/buckets.source.toolkit.fluxcd.io created
# customresourcedefinition.apiextensions.k8s.io/gitrepositories.source.toolkit.fluxcd.io created
# customresourcedefinition.apiextensions.k8s.io/helmcharts.source.toolkit.fluxcd.io created
# customresourcedefinition.apiextensions.k8s.io/helmreleases.helm.toolkit.fluxcd.io created
# customresourcedefinition.apiextensions.k8s.io/helmrepositories.source.toolkit.fluxcd.io created
# customresourcedefinition.apiextensions.k8s.io/kustomizations.kustomize.toolkit.fluxcd.io created
# customresourcedefinition.apiextensions.k8s.io/providers.notification.toolkit.fluxcd.io created
# customresourcedefinition.apiextensions.k8s.io/receivers.notification.toolkit.fluxcd.io created
# serviceaccount/helm-controller created
# serviceaccount/kustomize-controller created
# serviceaccount/notification-controller created
# serviceaccount/source-controller created
# clusterrole.rbac.authorization.k8s.io/crd-controller-flux-system created
# clusterrolebinding.rbac.authorization.k8s.io/cluster-reconciler-flux-system created
# clusterrolebinding.rbac.authorization.k8s.io/crd-controller-flux-system created
# service/notification-controller created
# service/source-controller created
# service/webhook-receiver created
# deployment.apps/helm-controller created
# deployment.apps/kustomize-controller created
# deployment.apps/notification-controller created
# deployment.apps/source-controller created
# unable to recognize "./cluster/base/flux-system": no matches for kind "Kustomization" in version "kustomize.toolkit.fluxcd.io/v1beta1"
# unable to recognize "./cluster/base/flux-system": no matches for kind "GitRepository" in version "source.toolkit.fluxcd.io/v1beta1"
# unable to recognize "./cluster/base/flux-system": no matches for kind "HelmRepository" in version "source.toolkit.fluxcd.io/v1beta1"
# unable to recognize "./cluster/base/flux-system": no matches for kind "HelmRepository" in version "source.toolkit.fluxcd.io/v1beta1"
# unable to recognize "./cluster/base/flux-system": no matches for kind "HelmRepository" in version "source.toolkit.fluxcd.io/v1beta1"
# unable to recognize "./cluster/base/flux-system": no matches for kind "HelmRepository" in version "source.toolkit.fluxcd.io/v1beta1"
```

:tada: **Congratulations** you have a Kubernetes cluster managed by Flux,
your Git repository is driving the state of your cluster.

## Verify Flux

Verify

```sh
kubectl --kubeconfig=${KUBECONFIG} get pods -n flux-system
flux --kubeconfig=${KUBECONFIG} get sources git
```

Manually sync Flux with your Git repository

```sh
flux --kubeconfig=${KUBECONFIG} reconcile source git flux-system
```

Check status

```sh
kubectl --kubeconfig=${KUBECONFIG} get kustomization -A
flux --kubeconfig=${KUBECONFIG} get helmrelease -A
```

## Verify ingress

If your cluster is not accessible to outside world you can provide a dns override for
`https://homer.${BOOTSTRAP_DOMAIN}` in your router
<!-- or update your hosts
file to verify the ingress controller is working.

```sh
echo "${BOOTSTRAP_METALLB_FRONTEND} ${BOOTSTRAP_DOMAIN} homer.${BOOTSTRAP_DOMAIN}" | sudo tee -a /etc/hosts
``` -->

Head over to your browser and you _should_ be able to access
`https://homer.${BOOTSTRAP_DOMAIN}`

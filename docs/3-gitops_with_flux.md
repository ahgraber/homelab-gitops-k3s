# :small_blue_diamond:&nbsp; GitOps (with Flux)

- [:small_blue_diamond:&nbsp; GitOps (with Flux)](#small_blue_diamond-gitops-with-flux)
  - [1. Verify Flux can be installed](#1-verify-flux-can-be-installed)
  - [2. Pre-create the `flux-system` namespace](#2-pre-create-the-flux-system-namespace)
  - [3. Add the Age key in-order for Flux to decrypt SOPS secrets](#3-add-the-age-key-in-order-for-flux-to-decrypt-sops-secrets)
  - [4. Create deploy key & add to github](#4-create-deploy-key--add-to-github)
  - [4. Export more environment variables for application configuration](#4-export-more-environment-variables-for-application-configuration)
  - [5. Create required files based on ALL exported environment variables](#5-create-required-files-based-on-all-exported-environment-variables)
  - [6. :mag:&nbsp; **Verify** all the above files have the correct information present](#6-mag-verify-all-the-above-files-have-the-correct-information-present)
  - [7. :closed_lock_with_key:&nbsp; Encrypt secrets with SOPS](#7-closed_lock_with_key-encrypt-secrets-with-sops)
    - [Create deploy key](#create-deploy-key)
    - [Encrypting with SOPS](#encrypting-with-sops)
  - [8. :mag:&nbsp; **Verify** all the above files are **encrypted** with SOPS](#8-mag-verify-all-the-above-files-are-encrypted-with-sops)
  - [9. Push your changes to git](#9-push-your-changes-to-git)
  - [10. Install Flux](#10-install-flux)
  - [Verify Flux](#verify-flux)
  - [Verify ingress](#verify-ingress)
  - [Next Steps -- :robot:&nbsp; Automation](#next-steps----robot-automation)

:round_pushpin: Here we will be installing [flux](https://toolkit.fluxcd.io/) after some quick
bootstrap steps.

> [Here](https://fluxcd.io/docs/flux-e2e/) is flux's explanation of its end-to-end commit flow.

## 1. Verify Flux can be installed

```sh
flux --kubeconfig=$(pwd)/kubeconfig check --pre
```

## 2. Pre-create the `flux-system` namespace

```sh
kubectl --kubeconfig="${KUBECONFIG}" create namespace flux-system --dry-run=client -o yaml | \
  kubectl --kubeconfig="${KUBECONFIG}" apply -f -
```

## 3. Add the Age key in-order for Flux to decrypt SOPS secrets

```sh
# cat ~/.config/sops/age/keys.txt |
cat "${SOPS_AGE_KEY_FILE}" |
    kubectl --kubeconfig="${KUBECONFIG}" \
    -n flux-system create secret generic sops-age \
    --from-file=age.agekey=/dev/stdin
```

## 4. Create deploy key & add to github

Generate key with :

```sh
ssh-keygen -t ecdsa -b 521 -C "github-deploy-key" -f ./cluster/github-deploy-key -q -P ""
```

Copy contents of `cluster/github-deploy-key.pub` to `deploy keys` section of github repo
`https://github.com/<username>/<repo_name>/settings/keys`

## 4. Export more environment variables for application configuration

> _Note:_ Exported variables go into `./tmpl/...`, where there are exported to settings and secrets
> in the next step

Here is a code blurb to quickly copy environmental variables into your .envrc. If using, **edit
before running or copying exports into .envrc**

```sh
cat >> .envrc << EOF

# The repo you created from this template
export BOOTSTRAP_GITHUB_REPOSITORY="https://github.com/ahgraber/homelab-gitops-k3s"
export GITHUB_USER="ahgraber"
export GITHUB_TOKEN="qwertyuiop123456789"
export BOOTSTRAP_DEFAULT_USER="admin"
export BOOTSTRAP_DEFAULT_EMAIL="k8s-at-home@gmail.com"
export BOOTSTRAP_DEFAULT_PASSWORD="changeme"

# Choose one of your domains or use a made up one
export BOOTSTRAP_DOMAIN="DOMAIN.COM"
# Cloudflare API token for DNS certification
export BOOTSTRAP_CLOUDFLARE_EMAIL="k8s-at-home@gmail.com"
export BOOTSTRAP_CLOUDFLARE_TOKEN="kpG6iyg3FS_du_8KRShdFuwfbwu3zMltbvmJV6cD"

# Pick a range of *UNUSED* IPs that are on the same network as your nodes
# Note: these cannot overlap with the kube-vip IP
export BOOTSTRAP_METALLB_FRONTEND="10.42.42.43"
export BOOTSTRAP_METALLB_RANCHER="10.42.42.44"
export SETTINGS_METALLB_MARIADB="10.42.42.45"
export SETTINGS_METALLB_POSTGRES="10.42.42.46"
export BOOTSTRAP_METALLB_LB_RANGE="10.42.42.200-10.42.42.242"


# Generate hashed user/password for traefik basicauth
export TRAEFIK_BASICAUTH='$(htpasswd -nb <USERNAME> <PASSWORD> | openssl base64)'
EOF
```

## 5. Create required files based on ALL exported environment variables

General procedure:

```zsh
# reload all env variables
direnv allow .

# create SOPS hook for secret encryption
envsubst < /path/to/templatefile.yaml.tmpl >! /path/to/outputfile.yaml
```

To run for all templates in repo:

```sh
bash ./scripts/substitute.sh
```

## 6. :mag:&nbsp; **Verify** all the above files have the correct information present

## 7. :closed_lock_with_key:&nbsp; Encrypt secrets with SOPS

> :round_pushpin: Variables defined in `cluster-secrets.yaml` and `cluster-settings.yaml` will be
> usable anywhere in your YAML manifests under `./cluster`

### Create deploy key

Create sops secret in `cluster/base/flux-system/github-deploy-key.sops.yaml` following
[template](../cluster/flux/flux-system/github-deploy-key.sops.yaml.example)

### Encrypting with SOPS

General procedure:

```sh
# Encrypt SOPS secrets
sops --encrypt --in-place /path/to/unencrypted_secrets.sops.yaml
```

To run for all templates in repo:

```sh
bash ./scripts/sops.sh
```

## 8. :mag:&nbsp; **Verify** all the above files are **encrypted** with SOPS

## 9. Push your changes to git

```sh
git add -A
git commit -m "initial commit"
git push
```

## 10. Install Flux

Apply deploy-key and sops-age secrets to cluster

```sh
cat "${SOPS_AGE_KEY_FILE}" |
    kubectl -n flux-system create secret generic sops-age --from-file=age.agekey=/dev/stdin
sops -d cluster/flux/flux-system/github-deploy-key.sops.yaml | kubectl apply -f -
```

Apply bootstrap and cluster kustomizations & force reconciliation

```sh
kubectl apply --kustomize ./cluster/bootstrap/
kubectl apply --kustomize ./cluster/flux/flux-system/
flux reconcile -n flux-system source git flux-cluster
flux reconcile -n flux-system kustomization flux-cluster
```

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

> For objects that have been preinstalled with ansible, we patch to allow helm to manage
> [tigera-operator](../cluster/core/tigera-operator/give_helm_ownership.sh)

[optional] Add alias for update

```sh
cat >> ~/.aliases.local << EOF
flux-update () {
flux --kubeconfig=$(pwd)/kubeconfig reconcile source git flux-system
sleep 50
kubectl --kubeconfig=$(pwd)/kubeconfig get kustomization -A
sleep 10
flux --kubeconfig=$(pwd)/kubeconfig get helmrelease -A
}
EOF
source ~/.aliases.local
```

## Verify ingress

If your cluster is not accessible to outside world you can provide a dns override for
`https://homer.${BOOTSTRAP_DOMAIN}` in your router

<!-- or update your hosts
file to verify the ingress controller is working.

```sh
echo "${BOOTSTRAP_METALLB_FRONTEND} ${BOOTSTRAP_DOMAIN} homer.${BOOTSTRAP_DOMAIN}" | sudo tee -a /etc/hosts
``` -->

Head over to your browser and you _should_ be able to access `https://homer.${BOOTSTRAP_DOMAIN}`

## Next Steps -- :robot:&nbsp; Automation

- [Renovate](https://www.whitesourcesoftware.com/free-developer-tools/renovate) is a very useful
  tool that when configured will start to create PRs in your Github repository when Docker images,
  Helm charts or anything else that can be tracked has a newer version. The configuration for
  renovate is located [here](./.github/renovate.json5).

There's also a couple Github workflows included in this repository that help automate some processes.

- [Renovate schedule](./.github/workflows/schedule-renovate.yaml) - workflow to annotate `HelmRelease`'s which allows
  [Renovate](https://www.whitesourcesoftware.com/free-developer-tools/renovate) to track Helm chart versions.
- [Megalinter](./.github/workflows/megalinter.yaml) - workflow to lint so cluster specifications
  remain properly formatted
- [Helm differ](./.github/workflows/helm-release-differ.yaml) - workflow to annotate PRs with the differences in helm files
  _NOTE:_ this requires [creating a private github bot](https://github.com/peter-evans/create-pull-request/blob/main/docs/concepts-guidelines.md#authenticating-with-github-app-generated-tokens)

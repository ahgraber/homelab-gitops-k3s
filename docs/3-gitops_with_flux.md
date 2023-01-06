# 🤖 GitOps (with Flux)

- [🤖 GitOps (with Flux)](#-gitops-with-flux)
  - [1. Verify Flux can be installed](#1-verify-flux-can-be-installed)
  - [2. Pre-create the `flux-system` namespace](#2-pre-create-the-flux-system-namespace)
  - [3. Add the Age key in-order for Flux to decrypt SOPS secrets](#3-add-the-age-key-in-order-for-flux-to-decrypt-sops-secrets)
  - [4. Create deploy key \& add to github](#4-create-deploy-key--add-to-github)
  - [4. Export more environment variables for application configuration](#4-export-more-environment-variables-for-application-configuration)
  - [5. Create required files based on ALL exported environment variables](#5-create-required-files-based-on-all-exported-environment-variables)
  - [6. 🔍 **Verify** all the above files have the correct information present](#6--verify-all-the-above-files-have-the-correct-information-present)
  - [7. 🔐 Encrypt secrets with SOPS](#7--encrypt-secrets-with-sops)
    - [Create deploy key](#create-deploy-key)
    - [Encrypting with SOPS](#encrypting-with-sops)
  - [8. 🔍 **Verify** all the above files are **encrypted** with SOPS](#8--verify-all-the-above-files-are-encrypted-with-sops)
  - [9. Push your changes to git](#9-push-your-changes-to-git)
  - [10. Install Flux](#10-install-flux)
  - [Verify Flux](#verify-flux)
  - [Manually sync Flux with your Git repository](#manually-sync-flux-with-your-git-repository)
  - [Verify ingress](#verify-ingress)
  - [📣 Post installation](#-post-installation)
    - [🌐 DNS](#-dns)
    - [🤖 Renovate](#-renovate)
    - [🪝 Github Webhook](#-github-webhook)

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
### allow direnv to import .env files
dotenv_if_exists ./.env

### Flux Config
export GITHUB_REPOSITORY=""
export GITHUB_USER=""
export GITHUB_TOKEN=""

### network ip allocations (calico)
export NET_NODE_CIDR="10.2.118.0/24"
export NET_POD_CIDR="10.42.0.0/16"
export NET_SVC_CIDR="10.43.0.0/16"

### Kube-Vip
export KUBE_VIP_ADDRESS="10.2.113.1"
export KUBE_VIP_IFACE="enp2s0"  # "ens192"

### K8s load-balancer IP allocations (metallb / kube-vip servicelb)
# Pick a range of unused IPs that are on the same network as your nodes
export LB_GATEWAY="10.2.113.2"
export LB_INGRESS="10.2.113.3"
export LB_AUTH="10.2.113.4"
# export LB_POSTGRES="10.2.113.5"
export LB_DEFAULT_RANGE="10.2.113.128-10.2.113.250"

### Cluster secrets
export SECRET_ADMIN_USER="admin"
export SECRET_ADMIN_EMAIL=""
export SECRET_DEFAULT_USER=""
export SECRET_DEFAULT_EMAIL=""
export SECRET_DEFAULT_PWD=""

export SECRET_DEFAULT_PWD_BASE64=''

export SECRET_DEFAULT_PWD_BCRYPT=''

export SECRET_DOMAIN=""

### Cloudflare API token for DNS certification
export SECRET_CLOUDFLARE_EMAIL=""
export SECRET_CLOUDFLARE_TOKEN=""
export SECRET_CLOUDFLARE_TUNNEL_TOKEN=""
export SECRET_CLOUDFLARE_TUNNEL_CREDS=""

### Generate hashed user/password for traefik basicauth:
# '$(htpasswd -nb $SECRET_ADMIN_USER $SECRET_DEFAULT_PWD | openssl base64)'
export TRAEFIK_BASICAUTH=''

### Email
export SECRET_SMTP_ADDRESS=""
export SECRET_SMTP_USER=""
export SECRET_SMTP_PWD=""
export SECRET_SMTP_SRV=""
export SECRET_SMTP_PORT=""
EOF
```

## 5. Create required files based on ALL exported environment variables

General procedure:

```zsh
# reload all env variables
direnv allow .

# create SOPS hook for secret encryption
envsubst < ./path/to/templatefile.yaml.tmpl >! ./path/to/outputfile.yaml
```

To run for all templates in repo:

```sh
bash ./scripts/substitute.sh
```

## 6. 🔍 **Verify** all the above files have the correct information present

## 7. 🔐 Encrypt secrets with SOPS

> :round_pushpin: Variables defined in `cluster-secrets.yaml` and `cluster-settings.yaml` will be
> usable anywhere in your YAML manifests under `./cluster`

### Create deploy key

Create sops secret in `cluster/base/flux-system/github-deploy-key.sops.yaml` following
[template](../kubernetes/bootstrap/github-deploy-key.sops.yaml.example)

### Encrypting with SOPS

General procedure:

```sh
# Encrypt SOPS secrets
sops --encrypt --in-place ./path/to/unencrypted_secrets.sops.yaml
```

To run for all templates in repo:

```sh
bash ./scripts/sops.sh
```

## 8. 🔍 **Verify** all the above files are **encrypted** with SOPS

## 9. Push your changes to git

```sh
git add -A
git commit -m "initial commit"
git push
```

## 10. Install Flux

📍 Review [ClusterTasks](./../.taskfiles/ClusterTasks.yaml) for insight into specific commands that will be run!

```sh
task cluster:install
```

## Verify Flux

```sh
# check flux installation
task cluster:pods -- -n flux-system

# look at all resources
task cluster:resources
# or view per-resource
task cluster:gitrepositories
task cluster:kustomizations
task cluster:helmreleases
task cluster:helmrepositories
task cluster:pods
task cluster:certificates
task cluster:ingresses
```

## Manually sync Flux with your Git repository

```sh
task cluster:reconcile
```

> For objects that have been preinstalled with ansible, patching may be required to allow helm management
> eg. [tigera-operator](../kubernetes/apps/networking/tigera-operator/give_helm_ownership.sh)

## Verify ingress

If your cluster is not accessible to outside world you can provide a dns override
for any service with an ingress in your router

Head over to your browser and you _should_ be able to access the service

## 📣 Post installation

### 🌐 DNS

📍 [external-dns](https://github.com/kubernetes-sigs/external-dns) will handle creating public DNS records.
By default, `echo-server` is the only public domain exposed on your Cloudflare domain.
In order to make additional applications public you must set an ingress annotation (see HelmRelease for `echo-server`).
Note: This is not required unless you need a record outside the purposes of your Kubernetes cluster (e.g. setting up MX records).

[k8s_gateway](https://github.com/ori-edge/k8s_gateway) is deployed on the IP choosen for `${LB_GATEWAY}`.
In order to test DNS you can point your client's DNS to the `${LB_GATEWAY}` IP address and load a deployed app in your browser.

You can also try debugging with the command `dig`, e.g. `dig @${LB_GATEWAY} <app_name>.${SECRET_DOMAIN}`
and you should get a valid answer containing your `${LB_INGRESS}` IP address.

If your router (or Pi-Hole, Adguard Home or whatever) supports conditional DNS forwarding (aka split-horizon DNS),
you may have DNS requests for `${SECRET_DOMAIN}` only point to the  `${LB_GATEWAY}` IP address.
This will ensure only DNS requests for `${SECRET_DOMAIN}` will only get routed to your [k8s_gateway](https://github.com/ori-edge/k8s_gateway)
service, providing DNS resolution to your cluster applications/ingresses.

To access services from the outside world, use Cloudflare Tunnels (formerly Argo Tunnel),
or port forward `80` and `443` in your router to the `${LB_INGRESS}` IP.
This _should_ provide access `https://echo-server.${BOOTSTRAP_CLOUDFLARE_DOMAIN}` from a device outside your LAN.

Of course, if nothing is working, that is expected. This is DNS after all!

### 🤖 Renovate

[Renovate](https://www.whitesourcesoftware.com/free-developer-tools/renovate) is a very useful
tool that when configured will start to create PRs in your Github repository when Docker images,
Helm charts or anything else that can be tracked has a newer version. The configuration for
renovate is located [here](./.github/renovate.json5).

To enable Renovate, click the 'Configure' button over at their [Github app page](https://github.com/apps/renovate)
and choose your repository. Over time Renovate will create PRs for out-of-date dependencies it finds.
Flux will deploy any merged PRs.

There are several Github workflows included in this repository that help automate some processes.

- [Renovate schedule](./.github/workflows/schedule-renovate.yaml) - workflow to annotate `HelmRelease`'s which allows
  Renovate to track Helm chart versions.
- [Megalinter](./.github/workflows/megalinter.yaml) - workflow to lint so cluster specifications
  remain properly formatted
- [Helm differ](./.github/workflows/helm-release-differ.yaml) - workflow to annotate PRs with the differences in helm files
  _NOTE:_ this requires [creating a private github bot](https://github.com/peter-evans/create-pull-request/blob/main/docs/concepts-guidelines.md#authenticating-with-github-app-generated-tokens)

### 🪝 Github Webhook

Flux is pull-based by design meaning it will periodically check your git repository for changes;
instead, using a webhook can enable Flux to update the cluster on `git push`.
In order to configure Github to send `push` events from your repository to the Flux webhook receiver you will need:

1. Webhook URL - Your webhook receiver will be deployed on `https://flux-webhook.${SECRET_DOMAIN}/hook/:hookId`.
   In order to find out your hook id you can run the following command:

    ```sh
    kubectl -n flux-system get receiver/github-receiver --kubeconfig=./kubeconfig
    # NAME              AGE    READY   STATUS
    # github-receiver   6h8m   True    Receiver initialized with URL: /hook/12ebd1e363c641dc3c2e430ecf3cee2b3c7a5ac9e1234506f6f5f3ce1230e123
    ```

    So if my domain was `testdomain.com`, the full url would look like this:

    ```text
    https://flux-webhook.testdomain.com/hook/12ebd1e363c641dc3c2e430ecf3cee2b3c7a5ac9e1234506f6f5f3ce1230e123
    ```

2. Webhook secret - Generate the secret token and populate the secret

   ```sh
   TOKEN=$(head -c 12 /dev/urandom | shasum | cut -d ' ' -f1)
   echo $TOKEN
   ```

    **Note:** Don't forget to update the `WEBHOOK_TOKEN` variable in your `.envrc` file
    and run `envsubst ...` ands `sops ...` to create the encrypted secret

Now that you have the webhook url and secret, it's time to set everything up on the Github repository side.
Navigate to the settings of your repository on Github, under "Settings/Webhooks" press the "Add webhook" button.
Fill in the webhook url and your secret.

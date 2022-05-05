# Cloudflare

## Argo Tunnel

Cloudflare Tunnel provides you with a secure way to connect your resources to Cloudflare
without a publicly routable IP address. With Tunnel, you do not send traffic to an external IP —
instead, a lightweight daemon in your infrastructure (cloudflared) creates outbound-only
connections to Cloudflare's edge.

### Prerequisites

Install the [cloudflared CLI](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/tunnel-guide#1-download-and-install-cloudflared)

### Deploying for k8s application

[github example docs](https://github.com/cloudflare/argo-tunnel-examples/tree/master/named-tunnel-k8s)
[documentation](https://developers.cloudflare.com/cloudflare-one/tutorials/many-cfd-one-tunnel#deploy-cloudflared)

1. If you haven't, login to you Cloudflare account to obtain a certificate.

   ```sh
   cloudflared tunnel login
   ```

   > This saves a cert.pem file to `${HOME}/.cloudflared/cert.pem`

2. Create a tunnel, change example-tunnel to the name you want to assign to your tunnel.

   ```sh
   # list existing
   cloudflared tunnel list
   # create new
   cloudflared tunnel create k8s-argo-tunnel
   ```

   > This writes a tunnel credential files to `${HOME}/.cloudflared/{GUID}.json`
   > and prints a `Tunnel Token` to the terminal

3. Extract the secret value and send to `.envrc` for use in secret template

   ```sh
   GUID=... # from above step
   SECRET_CLOUDFLARE_TUNNEL_CREDS=$(kubectl create secret generic tunnel-credentials \
   --from-file=credentials.json="${HOME}/.cloudflared/${GUID}.json" \
   --output=yaml \
   --dry-run=client | grep credentials.json | awk '{ print $2 }')
   echo "export SECRET_CLOUDFLARE_TUNNEL_CREDS=\"$SECRET_CLOUDFLARE_TUNNEL_CREDS\"" >> .envrc
   ```

4. Substitute and encrypt the secret

   ```sh
   # substitute
   envsubst < ./cluster/apps/networking/cloudflared/secret.sops.yaml.tmpl >! ./cluster/apps/networking/cloudflared/secret.sops.yaml

   # encrypt
   sops --encrypt --in-place ./cluster/apps/networking/cloudflared/secret.sops.yaml
   ```

5. (**START HERE IF TUNNEL ALREADY DEPLOYED**) Associate your Tunnel with a DNS record.

   ```sh
   cloudflared tunnel route dns k8s-argo-tunnel "<hostname>.${SECRET_DOMAIN}"
   ```

   > Repeat this process for all (sub)domains to be proxied over Cloudflared Tunnel

6. Deploy cloudflared by applying its manifest (managed by Flux kustomization).

   When Cloudflare receives traffic for the DNS or Load Balancing hostname you configured in the previous step,
   it will send that traffic to the cloudflareds running in this deployment.
   Those cloudflared instances will proxy the request to your app's Service.

## Terraform

TBD

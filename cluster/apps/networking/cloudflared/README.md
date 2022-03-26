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
   > **Save this tunnel token to the .envrc** for use in k8s secret creation

3. Create a Kubernetes secret using the tunnel token and secret template

   ```sh
   # substitute
   envsubst < ./secret.sops.yaml.tmpl > ./secret.sops.yaml
   # encrypt with sops
   sops --encrypt --in-place ./secret.sops.yaml
   ```

   > use scripts to substitute & encrypt all at once:
   >
   > ```sh
   > ./scripts/substitute.sh && ./scripts/sops.sh
   > ```

4. Associate your Tunnel with a DNS record.

   ```sh
   cloudflared tunnel route dns k8s-argo-tunnel "<hostname>.${SECRET_DOMAIN}"
   ```

   > Repeat this process for all (sub)domains to be proxied over Cloudflared Tunnel

5. Deploy cloudflared by applying its manifest (managed by Flux kustomization).

   When Cloudflare receives traffic for the DNS or Load Balancing hostname you configured in the previous step,
   it will send that traffic to the cloudflareds running in this deployment.
   Those cloudflared instances will proxy the request to your app's Service.

6. Examine status of the pod.

   <!-- markdownlint-disable -->
   ```sh
   $ kubectl get pods
   NAME                                  READY   STATUS    RESTARTS   AGE
   cloudflared-57746f77fd-frc99          1/1     Running   0          12m
   cloudflared-57746f77fd-xht8n          1/1     Running   0          12m
   httpbin-deployment-67f749774f-42tqj   1/1     Running   0          20h

   $ kubectl logs $(kubectl get pod -l app=cloudflared -o jsonpath="{.items[0].metadata.name}")
   2021-05-04T17:39:49Z INF Starting tunnel tunnelID=ef824aef-7557-4b41-a398-4684585177ad
   2021-05-04T17:39:49Z INF Version
   2021-05-04T17:39:49Z INF GOOS: linux, GOVersion: go1.15.7, GoArch: amd64
   2021-05-04T17:39:49Z INF Settings: map[config:/etc/cloudflared/config/config.yaml cred-file:/etc/cloudflared/creds/credentials.json credentials-file:/etc/cloudflared/creds/credentials.json metrics:0.0.0.0:2000 no-autoupdate:true]
   2021-05-04T17:39:49Z INF Generated Connector ID: 4c5dc5d3-8e10-480e-ac74-e385e591553e
   2021-05-04T17:39:49Z INF Initial protocol h2mux
   2021-05-04T17:39:49Z INF Starting metrics server on [::]:2000/metrics
   2021-05-04T17:39:49Z INF Connection 1daced2f-466c-4610-8ba6-7642a8ddec68 registered connIndex=0 location=MCI
   2021-05-04T17:39:50Z INF Connection 1a5276bc-3313-4bb7-a677-d93deccab24f registered connIndex=1 location=DFW
   2021-05-04T17:39:51Z INF Connection aa7adacc-e855-4b11-bf41-e113419b7ef4 registered connIndex=2 location=MCI
   2021-05-04T17:39:51Z INF Connection a8055c76-2a90-4be5-8dc9-ebaa5c58fb5f registered connIndex=3 location=DFW
   ```
<!-- markdownlint-enable -->

## Terraform

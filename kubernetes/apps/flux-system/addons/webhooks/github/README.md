# GitHub Webhook Configuration

This directory contains manifests for configuring GitHub webhooks to trigger Flux automatic syncs when your repository is updated.

## Overview

When you push changes to your GitHub repository, the webhook delivers a notification to the Flux webhook receiver. The receiver then triggers a reconciliation of the configured GitRepository and Kustomization resources, pulling in your changes without delay.

## Components

- `receiver.yaml` — Flux `Receiver` resource that defines how to handle GitHub webhook events
- `ingress.yaml` — Ingress route exposing the webhook receiver to the internet
- `httproute.yaml` — Gateway API HTTPRoute (alternative/supplement to Ingress)
- `kustomization.yaml` — Kustomize composition
- `secret.sops.yaml` / `secret.sops.yaml.tmpl` — Sealed secret containing the GitHub webhook token

## Prerequisites

1. A GitHub Webhook Secret generated in your GitHub repository settings
2. A publicly accessible domain/URL pointing to your cluster (e.g., `flux-webhook.${bootstrap_cloudflare_domain}`)
3. TLS certificate for the webhook URL (handled by cert-manager; see root README for certificate setup)
4. SOPS and Age configured for secret encryption (see root README initial configuration steps)
5. Flux bootstrapped in your cluster (`task flux:bootstrap`)

## Setup Steps

### 1. Generate a GitHub Webhook Secret

On your GitHub repository, go to **Settings → Webhooks** and either:

- Create a new webhook, or
- Copy the existing webhook's Secret

### 2. Create the Secret

The webhook token should be stored in `secret.sops.yaml`. Use `secret.sops.yaml.tmpl` as a template:

```bash
# Copy the template
cp secret.sops.yaml.tmpl secret.sops.yaml

# Set the GitHub webhook secret (generate this in GitHub repo settings → Webhooks)
export GH_WEBHOOK_TOKEN="your-github-webhook-secret"
envsubst < secret.sops.yaml.tmpl > secret.sops.yaml.tmp && mv secret.sops.yaml.tmp secret.sops.yaml

# Encrypt with sops/age (requires SOPS_AGE_KEY_FILE environment variable set)
sops -e secret.sops.yaml > secret.sops.yaml.tmp && mv secret.sops.yaml.tmp secret.sops.yaml
```

⚠️ **Important**: The secret file must be encrypted before pushing to git. Unencrypted secrets will be rejected.

```bash
# Verify the file is encrypted (should contain "ENC[" at the top)
head -5 secret.sops.yaml

# Add and push to git
git add secret.sops.yaml
git commit -m "chore: add github webhook secret"
git push
```

For more details on SOPS and Age setup, see the [root README](../../../README.md).

### 3. Configure the GitHub Repository Webhook

In your GitHub repository (**Settings → Webhooks**):

1. **Payload URL**: Obtain the full webhook path from the Receiver status:

   ```bash
   kubectl -n flux-system get receiver github-webhook -o jsonpath='{.status.webhookPath}'
   # Output: /hook/123abc...
   ```

   Piece together the full URL:

   ```txt
   https://flux-webhook.${bootstrap_cloudflare_domain}/hook/123abc...
   ```

2. **Content type**: `application/json`

3. **Secret**: Your webhook token from step 1

4. **Events**: Select "Just the push event" (or "Push events" + others as needed)

5. **Active**: Enabled ✓

### 4. Update Ingress Configuration

Edit `httproute.yaml` to match your domain and environment variables:

```yaml
spec:
  hostnames:
    - flux-webhook.${SECRET_DOMAIN}        # Will be substituted by your environment
```

The domain uses the `${SECRET_DOMAIN}` placeholder which should be replaced via your kustomization build process or environment. Ensure your DNS (via Cloudflare external-dns) points to your Ingress external IP.

**For Gateway API routing** (HTTPRoute in `httproute.yaml`):

- Routes to `envoy-external` Gateway in the `network` namespace
- Ensure the gateway is properly configured with TLS

### 5. Verify the Receiver Resources

The `receiver.yaml` currently reconciles:

- `GitRepository`: `home-kubernetes` (flux-system namespace)
- `Kustomization`: `cluster` and `apps` (flux-system namespace)

Update the `resources` list if your repository or Kustomization names differ:

```yaml
spec:
  resources:
    - apiVersion: source.toolkit.fluxcd.io/v1
      kind: GitRepository
      name: YOUR_GIT_REPO_NAME # defined in kubernetes/flux/config/cluster.yaml
      namespace: flux-system
    - apiVersion: kustomize.toolkit.fluxcd.io/v1
      kind: Kustomization
      name: YOUR_KUSTOMIZATION_NAME
      namespace: flux-system
```

## Testing

### Verify Flux is running

Before testing the webhook, ensure Flux is bootstrapped and running:

```bash
flux check --pre

kubectl -n flux-system get pods
# Should see: helm-controller, kustomize-controller, notification-controller, source-controller
```

### Test the webhook manually

Once deployed, you can test by pushing to your GitHub repository or using GitHub's webhook test feature:

1. Go to **Settings → Webhooks** on your repository
2. Click the webhook
3. Click **"Recent Deliveries"** and then **"Redeliver"** on a recent ping/push event
4. Watch the cluster for reconciliation (see logs below)

### Watch the Flux logs

```bash
# Watch receiver logs (should see "POST /hook/..." with 202 responses)
kubectl -n flux-system logs -f deployment/webhook-receiver

# Watch git repository pull
kubectl -n flux-system logs -f deployment/source-controller -c source-controller

# Watch kustomization reconciliation (triggered by webhook)
kubectl -n flux-system logs -f deployment/kustomize-controller

# Check the Receiver status and last reconciliation time
kubectl -n flux-system describe receiver github-webhook
```

### Check reconciliation status

```bash
# GitRepository pull status
kubectl -n flux-system describe gitrepository home-kubernetes

# Check if git pull was triggered recently
kubectl -n flux-system get gitrepository home-kubernetes -o jsonpath='{.status.lastUpdateTime}'

# Kustomization reconciliation status (should show recent timestamps)
kubectl -n flux-system describe kustomization cluster
kubectl -n flux-system describe kustomization apps
```

## Troubleshooting

### Webhook not triggering reconciliation

1. **Flux not running or bootstrapped**:

   ```bash
   flux check --pre
   kubectl -n flux-system get pods | grep -E "source-controller|kustomize-controller"
   ```

   If not running, bootstrap Flux first: `task flux:bootstrap`

2. **Check Ingress is accessible**:

   ```bash
   kubectl -n flux-system get ingress
   # Verify the external IP/hostname is reachable from the internet
   curl -I https://flux-webhook.${SECRET_DOMAIN}/hook/
   ```

   Ensure DNS is properly configured (Cloudflare external-dns should have created the DNS record)

3. **Verify the receiver secret is correct**:

   ```bash
   # Check secret exists
   kubectl -n flux-system get secret github-webhook-token

   # Verify it's been properly decrypted by Flux
   kubectl -n flux-system get secret github-webhook-token -o yaml | grep token
   ```

4. **Verify Receiver resource**:

   ```bash
   kubectl -n flux-system describe receiver github-webhook
   # Should show status.webhookPath and status.lastHandledReconcileTime
   ```

5. **Check GitHub webhook delivery**:

   - Go to **Settings → Webhooks** on your repository
   - Click the webhook and scroll to **"Recent Deliveries"**
   - Click any delivery to see the request/response
   - Look for:
     - Status: `202 Accepted` (successful delivery)
     - Response shows webhook path accepted

6. **Check receiver pod logs**:

   ```bash
   kubectl -n flux-system logs deployment/webhook-receiver --tail=50 -f
   # Should show "POST /hook/[hash] 202" for successful requests
   ```

7. **Verify receiver recognizes the secret**:

   ```bash
   kubectl -n flux-system logs deployment/webhook-receiver | grep -i "hmac\|signature"
   # Should not show signature errors if secret is correct
   ```

### TLS/Certificate Issues

- Ensure cert-manager is running:

  ```bash
  kubectl -n cert-manager get pods
  ```

- Check certificate status:

  ```bash
  kubectl -n flux-system get certificate
  kubectl -n flux-system describe certificate github-webhook
  # Should show "True" condition with "Certificate issued successfully"
  ```

- If certificate is not issued, check cert-manager logs:

  ```bash
  kubectl -n cert-manager logs -f deployment/cert-manager
  ```

- For Let's Encrypt issues, verify you're not using the staging environment in production (see root README for certificate setup)

### Secret Not Decrypting

- Verify the age key is available on cluster:

  ```bash
  kubectl -n flux-system get secret sops-age
  ```

- Ensure `secret.sops.yaml` is encrypted with the correct key:

  ```bash
  head -5 secret.sops.yaml
  # Should show "ENC[" indicating encryption
  ```

- Re-encrypt the secret if needed:

  ```bash
  sops -d secret.sops.yaml | sops -e /dev/stdin > secret.sops.yaml.tmp && mv secret.sops.yaml.tmp secret.sops.yaml
  git add secret.sops.yaml && git commit -m "chore: re-encrypt webhook secret"
  git push
  ```

## References

- [Root README](../../../README.md) — Cluster setup, SOPS/Age configuration, and initial Flux bootstrap instructions
- [Flux Notification Webhook Receiver docs](https://fluxcd.io/flux/components/notification/receiver/)
- [Flux GitHub webhook guide](https://fluxcd.io/flux/guides/webhook-receivers/#define-a-git-repository-receiver)
- [GitHub Webhooks docs](https://docs.github.com/en/developers/webhooks-and-events/webhooks)
- [SOPS documentation](https://github.com/getsops/sops)
- [Age documentation](https://github.com/FiloSottile/age)

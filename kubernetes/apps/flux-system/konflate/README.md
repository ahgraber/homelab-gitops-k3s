# Konflate

[Konflate](https://github.com/home-operations/konflate) is a read-only pull request review tool for Flux.
It renders every open PR against `main` with [flate](https://github.com/home-operations/flate) (the same tool the `Flate` CI workflow uses) and shows the diff of the _rendered_ Kubernetes resources — not the raw file diff.
A one-line HelmRelease bump shows up as the actual resources that change, with blast-radius counts, container image changes, render failures, and danger flags (data-loss, RBAC, immutable-field changes).

- **UI**: `https://konflate.${SECRET_DOMAIN}` (internal gateway only)
- **Webhook**: `https://konflate-webhook.${SECRET_DOMAIN}/hooks` (external gateway, `/hooks` path only)
- **Chart**: `oci://ghcr.io/home-operations/charts/konflate`
- **Reference**: [onedr0p/home-ops konflate](https://github.com/onedr0p/home-ops/tree/main/kubernetes/apps/flux-system/konflate)

## Configuration

- `config.repo: github://ahgraber/homelab-gitops-k3s` — the repo it watches.
- `config.clusterPath` is left empty (repo root) because this repo's Flux `spec.path` values are root-relative (`./kubernetes/...`), which is what flate resolves against.
- `config.verifyImages: true` — HEAD-checks each newly referenced container image against its registry to catch typo'd or not-yet-pushed tags before they ImagePullBackOff.
- **Write-back is on** (`statusChecks` + `prComments`): konflate posts a Check Run named `Konflate` on each PR head and one summary comment per PR, edited in place on every re-render.
  Both link back to `config.publicUrl`.
- **A repo-level webhook drives renders.**
  Each push to a PR reaches `POST /hooks` and re-renders within seconds; the 30m poll (`refreshInterval`) stays as a missed-webhook backstop.
  Only `/hooks` is exposed externally — the [webhook HTTPRoute](app/httproute.yaml) routes that one path through the Cloudflare tunnel, while the UI stays internal.
  This mirrors the Flux `github-webhook` receiver, so every GitHub-to-cluster delivery lives under one repo Settings → Webhooks page.
- `persistence` (2Gi ceph-block) keeps rendered diffs, the bare git mirror, and flate's helm caches across restarts.

## Setup

Konflate needs a GitHub App (write-back plus read auth) and a repo-level webhook (render triggers).
The App and webhook are separate on purpose: the webhook joins the Flux receiver under repo Settings → Webhooks, while the App carries only the credential konflate writes with.
All secrets live in one 1Password item, so the manifests never change when they rotate.

### 1. Create the GitHub App

1. Go to GitHub → Settings → Developer settings → GitHub Apps → **New GitHub App**.
2. Name it (e.g. `konflate-homelab`), set any homepage URL, and **uncheck "Active" under Webhook** — the repo webhook (step 3) delivers events, not the App.
3. Grant two repository permissions: **Checks: Read and write** (the Check Run) and **Pull requests: Read and write** (the summary comment).
4. Create the App, copy its **Client ID** (`Iv23...`), and generate a **private key** (downloads a `.pem` file).
5. Install the App on **only** `ahgraber/homelab-gitops-k3s`.

### 2. Generate a webhook secret

Generate a random HMAC secret GitHub signs its webhooks with: `openssl rand -hex 32`.
Konflate rejects any delivery that fails this signature, so `/hooks` can safely face the internet.

### 3. Add the repo-level webhook

Go to the repo → Settings → Webhooks → **Add webhook** (the same page as the Flux `github-webhook`):

- **Payload URL**: `https://konflate-webhook.${SECRET_DOMAIN}/hooks`
- **Content type**: `application/json`
- **Secret**: the value from step 2
- **Events**: choose "Let me select individual events" and check **only Pull requests**.
  That is the sole event konflate renders on — `synchronize` re-renders a PR when its head advances, and open/close/reopen re-list.
  Do **not** add "Pushes": konflate ignores it (degrading to a wasteful full re-list), and pushing to a PR branch already fires a pull-request event.
  Optionally add **Check runs**, **Check suites**, and **Statuses** if you want konflate's UI to reflect other CI checks' rollup on a PR; it is not needed for rendering.

### 4. Create the 1Password item

Create `flux-system.konflate` in the **homelab** vault with four fields:

| Field           | Type          | Value                                              |
| --------------- | ------------- | -------------------------------------------------- |
| `token`         | concealed     | a read-only PAT, or blank (see below)              |
| `webhookSecret` | concealed     | the HMAC secret (step 2)                           |
| `appClientId`   | text          | the App's Client ID (step 1)                       |
| `privateKey`    | **concealed** | the `.pem` key file, **base64-encoded** (see note) |

Store `privateKey` **base64-encoded in a concealed field**.
A plain-text field would render the PEM in cleartext in the vault, and a concealed field is single-line — so it cannot hold the multi-line PEM directly.
Base64 collapses the key to one line that a concealed field holds safely; the ExternalSecret runs it back through `b64dec` to the raw PEM konflate expects.
Encode it with:

```sh
base64 -i <path-to>.private-key.pem | tr -d '\n'
```

Or set it directly with the `op` CLI:

```sh
op item edit "flux-system.konflate" --vault homelab \
  "privateKey[password]=$(base64 -i <path-to>.private-key.pem | tr -d '\n')"
```

The ExternalSecret maps these to `KONFLATE_TOKEN`, `KONFLATE_WEBHOOK_SECRET`, `KONFLATE_APP_CLIENT_ID`, and `KONFLATE_APP_PRIVATE_KEY`; the chart consumes them via `secret.existingSecret`.
Konflate auto-detects the App's installation, so no installation ID is needed.
The App already authenticates reads (raising the API rate limit), so `token` is optional — set a read-only PAT only if you want a fallback for when the App is unavailable.

## Dependencies

- rook-ceph (cache/state PVC)
- external-secrets (`onepassword` ClusterSecretStore)
- envoy-internal gateway (`network` namespace) — the UI
- envoy-external gateway + cloudflared tunnel (`network` namespace) — the `/hooks` webhook
- kube-prometheus-stack (ServiceMonitor)

## Gotchas

- **Single instance only** — konflate holds PR/diff state in memory and uses an RWO cache PVC; the Deployment uses `strategy: Recreate` and the chart rejects `replicaCount > 1`.
- **Fork PRs are listed but never rendered** (`renderForkPrs: false`, the default) — rendering a fork runs untrusted code through flate (SSRF surface).
  Renovate PRs are branches, not forks, so they render fine.
- **Write-back credentials are checked once at startup.**
  A bad or missing App credential disables write-back with a single log line rather than failing renders; restart the pod after fixing the 1Password item.
- **PR-comment links only resolve from the home network** — `publicUrl` points at the internal-only hostname, so the "view in konflate" links need split DNS.
  The check and comment still post regardless.
- **Konflate's HTTP surface stays read-only** even with write-back on; only its own render loop posts, and the "copy to merge" button just puts a `gh pr merge ...` command on your clipboard.
- With write-back live, the `flux-local` diff workflow is redundant; keep the `Flate` workflow, which validates rather than diffs.

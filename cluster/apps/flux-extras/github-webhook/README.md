# Github Webhook

A github webhook can send notifications to a [Flux receiver](https://fluxcd.io/docs/guides/webhook-receivers/) when a git event occurs.
This means that Flux can be notified when a commit happens and automatically reconcile,
reducing the need to wait for the timed reconciliation or manually call for a sync.

## Create receiver

1. Create a token

   ```sh
   TOKEN=$(head -c 12 /dev/urandom | shasum | cut -d ' ' -f1)
   echo $TOKEN
   ```

2. Create secret using token
3. Apply `github-webhook` kustomization

## Create webhoook

1. In Github repo > Settings > Create Webhook
2. Set `payload url` to the url specified in the ingress
3. Set `token` to the token created above

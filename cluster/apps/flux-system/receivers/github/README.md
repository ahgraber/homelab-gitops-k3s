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

## Create webhoook in Github settings

1. In Github repo > Settings > Create Webhook

2. Set `payload url` to the url specified in the ingress + the `/hook/<random>`:
   i.e., `https://flux-receiver.example.com/hook/0p39dj3nck3udn3m`

   The path can be found with:

   ```sh
   kubectl -n flux-system get receiver/github-receiver
   ```

3. Set `token` to the token created above

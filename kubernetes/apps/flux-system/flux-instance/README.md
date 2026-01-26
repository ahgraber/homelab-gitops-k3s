# Flux Instance

The instance is the current incarnation of the Flux cluster.
New instances may require updating the GitHub webhook.

## 🪝 GitHub Webhook

By default Flux will periodically check your git repository for changes.
In order to have Flux reconcile on `git push` you must configure GitHub to send `push` events.

1. Follow [FluxCD instructions](https://fluxcd.io/flux/guides/webhook-receivers/#define-a-git-repository-receiver) to generate a token.

2. Obtain the webhook path

   📍 _Hook id and path should look like `/hook/123abc123abc...`_

   ```sh
   kubectl -n flux-system get receiver github-webhook -o jsonpath='{.status.webhookPath}'
   ```

3. Piece together the full URL with the webhook path appended

   ```text
   https://flux-webhook.${bootstrap_cloudflare_domain}/hook/123abc123abc...
   ```

4. Navigate to the settings of your repository on GitHub, under "Settings/Webhooks" press the "Add webhook" button.
   Fill in the webhook url and your `bootstrap_flux_github_webhook_token` secret and save.

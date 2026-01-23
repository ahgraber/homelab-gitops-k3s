# Bitwarden ESO migration tooling (Phase 2)

This doc describes the Phase 2 migration tooling.
It crawls SOPS secrets, pushes them to Bitwarden, and generates ExternalSecrets without persisting plaintext to disk.

## Goals

- Translate SOPS-managed Kubernetes Secrets into Bitwarden items/fields.
- Keep plaintext out of disk by decrypting only during the push step.
- Persist an inventory that can be reused to generate ExternalSecrets.

## Requirements

- `sops` installed locally.
- Bitwarden Secrets Manager account exists.
- A Bitwarden project exists in that account.
- A Bitwarden machine account exists with read/write permissions.
- `BWS_ACCESS_TOKEN` is available in the environment for the machine account.
- `BWS_ORG_ID` is available to scope SDK requests.
- Bitwarden Secrets Manager CLI (`bws`) installed and authenticated.

## Inventory format

The crawler writes `inventory.json` to a chosen output directory.
It is metadata-only and does not store plaintext values.
`project_id` is stored at the top level; entries do not include it.

Example:

```json
{
  "version": 1,
  "root": "kubernetes/apps",
  "project_id": "<bitwarden-project-id>",
  "entries": [
    {
      "sops_path": "kubernetes/apps/default/homebox/app/secret.sops.yaml",
      "namespace": "default",
      "app": "homebox",
      "purpose": "app",
      "item_name": "default/homebox-app",
      "fields": [
        "HBOX_MAILER_USERNAME",
        "HBOX_MAILER_PASSWORD"
      ],
      "secret_id": null,
      "ks_path": "kubernetes/apps/default/homebox/ks.yaml",
      "helmrelease_path": "kubernetes/apps/default/homebox/app/helmrelease.yaml"
    }
  ]
}
```

## Crawl workflow

Crawl a directory and build the inventory:

```bash
./scripts/bws/crawl.py \
  --dir kubernetes/apps \
  --output-dir ./migration-out \
  --project-id <bitwarden-project-id>
```

Notes:

- The crawler infers namespace/app using the nearest `ks.yaml` and `helmrelease.yaml`.
- Bitwarden keys are `{namespace}/{app}-{purpose}`; `secret.sops.yaml` maps to `purpose=app`.
- The inventory is metadata only (no plaintext values).
- Each SOPS file is pushed as a single Bitwarden secret with key `{namespace}/{app}-{purpose}` and a note of `{namespace}/{app}`.
- `--output-dir` defaults to `--dir`; `BWS_PROJECT_ID` can supply the default project ID.

## Push workflow

Push inventory entries to Bitwarden using `bws` (decrypts SOPS locally and streams values):

```bash
./scripts/bws/push.py \
  --inventory ./migration-out/inventory.json
```

Notes:

- The script lists existing secrets and asks whether to apply all, skip all, or prompt per secret.
- Each entry is stored as a single key/value secret whose value is JSON for the SOPS fields.
- Use `--no-write-inventory` to avoid modifying the inventory file.
- `bws` is expected on PATH and authenticated via `BWS_ACCESS_TOKEN` or local config.

## ExternalSecret generation

Generate `ExternalSecret` manifests next to each SOPS file:

```bash
./scripts/bws/externalsecrets.py \
  --inventory ./migration-out/inventory.json
```

Notes:

- Requires `project_id` and the unique Bitwarden key to build `remoteRef.key`.
- Output files are derived from the SOPS filename, e.g. `secret-oidc.sops.yaml` -> `secret-oidc.externalsecret.yaml`.
- The target Secret name is `app` or `app-<purpose>` in the namespace.

## Legacy tooling

The previous mapping-based helper (`scripts/bws/migrate.py`) is still available but is not part of the default workflow above.

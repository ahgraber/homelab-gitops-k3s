# Bitwarden ESO migration tooling (Phase 2)

This doc describes the Phase 2 migration tooling. It prepares and validates migrations without changing any secrets in Bitwarden or Kubernetes.

## Goals

- Translate SOPS-managed Kubernetes Secrets into Bitwarden items/fields.
- Keep plaintext out of disk by streaming decrypted values in memory.
- Provide dry-run output and optional idempotency checks.

## Requirements

- `sops` installed locally.
- A Bitwarden CLI/SDK command available when you are ready to apply (ex: `bws`).

## Mapping file format

The migration helper reads a JSON mapping file. Each entry defines:

- `name`: Bitwarden item name following `{namespace}-{app}-{purpose}`.
- `namespace`: Kubernetes namespace for tracking and filtering.
- `sops_path`: path to the SOPS-encrypted Secret manifest.
- `fields`: mapping of Bitwarden field name to SOPS key (under `stringData` or `data`).
- `project_id` (optional): overrides the default project ID.

Example:

```json
{
  "defaults": {
    "project_id": "<bitwarden-project-id>"
  },
  "entries": [
    {
      "name": "default-homebox-app",
      "namespace": "default",
      "sops_path": "kubernetes/apps/default/homebox/app/secret.sops.yaml",
      "fields": {
        "username": "HOMEB0X_USERNAME",
        "password": "HOMEB0X_PASSWORD"
      }
    }
  ]
}
```

Template: `docs/bitwarden-eso-migration-map.example.json`.

## Dry-run workflow (default)

Run the helper to decrypt SOPS files and show a redacted plan:

```bash
./scripts/bitwarden-eso-migrate.py \
  --mapping docs/bitwarden-eso-migration-map.example.json
```

By default, values are redacted and no external commands are executed.

## Apply workflow (explicit)

When ready, provide a command template that pushes values to Bitwarden. The helper:

- Formats the command using `{item_name}`, `{project_id}`, and `{namespace}` placeholders.
- Passes the JSON payload to stdin when `--stdin` is set.
- Optionally runs a check command to skip existing items unless `--force` is used.

Example (confirm exact CLI flags for your `bws` version):

```bash
./scripts/bitwarden-eso-migrate.py \
  --mapping docs/bitwarden-eso-migration-map.example.json \
  --apply \
  --command-template 'bws <create-command> --project-id {project_id} --name {item_name} --value @-' \
  --stdin \
  --check-template 'bws <check-command> --project-id {project_id} --name {item_name}'
```

Notes:

- `--check-template` provides idempotency: a zero exit code means "exists" and is skipped.
- `--force` applies even if the check succeeds.
- Use `--show-values` only when you explicitly need plaintext output.

## Optional in-cluster PushSecret pattern

If you prefer to push from inside the cluster, use an ESO `PushSecret` with a temporary Secret:

1. Create a temporary Secret from decrypted values.
2. Apply a `PushSecret` targeting Bitwarden.
3. Verify the Bitwarden item, then delete the temporary Secret and `PushSecret`.

This path is optional and should only be used for controlled, short-lived operations.

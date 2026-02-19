# 1Password ESO migration tooling

This doc describes the migration tooling used to move SOPS-managed Kubernetes
secrets into 1Password for External Secrets Operator (ESO).

Workflow:

1. Crawl SOPS files into metadata inventory.
2. Push decrypted values to 1Password items with `op`.
3. Generate `ExternalSecret` manifests that map item fields to K8s secret keys.

## Goals

- Translate SOPS-managed Kubernetes Secrets into 1Password item fields.
- Keep plaintext out of disk by decrypting only during the push step.
- Persist an inventory that can be reused to generate ExternalSecrets.

## Requirements

- `sops` installed locally.
- 1Password account and dedicated vault (for example, `homelab`).
- 1Password CLI (`op`) installed and authenticated.
- `OP_VAULT` set in the environment (or pass `--vault`).

## Inventory format

The crawler writes `inventory.json` to a chosen output directory.
It is metadata-only and does not store plaintext values.

Example:

```json
{
  "version": 1,
  "root": "kubernetes/apps",
  "vault": "homelab",
  "entries": [
    {
      "sops_path": "kubernetes/apps/default/homebox/app/secret.sops.yaml",
      "namespace": "default",
      "app": "homebox",
      "purpose": "app",
      "section": null,
      "item_name": "default.homebox",
      "fields": [
        "HBOX_MAILER_USERNAME",
        "HBOX_MAILER_PASSWORD"
      ],
      "item_id": null,
      "ks_path": "kubernetes/apps/default/homebox/ks.yaml",
      "helmrelease_path": "kubernetes/apps/default/homebox/app/helmrelease.yaml"
    }
  ]
}
```

## Crawl workflow

Crawl a directory and build the inventory:

```bash
./scripts/onepassword/crawl.py \
  --dir kubernetes/apps \
  --output-dir ./migration-out \
  --vault homelab
```

Notes:

- Namespace/app inference uses nearest `ks.yaml` and `helmrelease.yaml`.
- `op` references follow `op://homelab/<namespace>.<appname>/[section]/<field>`.
- Item titles should be `{namespace}.{appname}` and section should represent purpose when needed.
- The crawler stores this as `section` metadata (`null` for `purpose=app`).
- Separator preference between namespace and app name: `.`, then `_`, then `-`.
- `--output-dir` defaults to `--dir`; `OP_VAULT` can provide the default vault.

## Push workflow

Push inventory entries to 1Password using `op`:

```bash
./scripts/onepassword/push.py \
  --inventory ./migration-out/inventory.json
```

Notes:

- The script decrypts each SOPS file locally and sends item templates to `op` via stdin.
- Entries sharing the same `item_name` are merged into one 1Password item.
- Entries with a non-null `section` are written into that section on the item.
- If two source files map to the same `item_name` and contain different values for the same field label, that item is skipped and reported as a conflict.
- ESO's 1Password provider resolves by field label and ignores section names, so field labels must stay unique within an item.
- Existing item titles prompt for apply mode: per-item, apply-all, or skip-all.
- Item IDs are written back to the inventory unless `--no-write-inventory` is used.

## ExternalSecret generation

Generate `ExternalSecret` manifests next to each SOPS file:

```bash
./scripts/onepassword/externalsecrets.py \
  --inventory ./migration-out/inventory.json
```

Notes:

- Output files are derived from SOPS filename, e.g.
  `secret-oidc.sops.yaml` -> `secret-oidc.externalsecret.yaml`.
- Generated manifests target `ClusterSecretStore` named `onepassword`.
- For each key, `remoteRef.key` is the item title and `remoteRef.property` is the field label.

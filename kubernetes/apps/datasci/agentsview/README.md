# AgentsView

[AgentsView](https://github.com/kenn-io/agentsview) indexes coding-agent session transcripts (Claude Code, Codex, Copilot CLI, and others) and reports token usage, cost, and searchable history.

It is local-first: every workstation runs its own copy against its own SQLite archive.
This deployment provides a shared aggregation point.
Each workstation pushes its sessions into a central PostgreSQL database, and the cluster serves one read-only dashboard over the union of them at `https://agentsview.${SECRET_DOMAIN}`.

## Architecture

```text
workstation A ─ agentsview pg push ─┐
workstation B ─ agentsview pg push ─┼─► datasci16 (PostgreSQL) ◄── agentsview pg serve (this app)
workstation C ─ agentsview pg push ─┘        ▲                              │
                                     datasci-db.${SECRET_DOMAIN}    agentsview.${SECRET_DOMAIN}
                                        (LAN, 10.2.118.7)              (envoy-internal)
```

- **Sync direction is one-way.**
  Workstations push; nothing flows back.
  The dashboard is read-only — starring and pinning happen locally and travel with the next push.
- **The pod holds no state.** `pg serve` reads everything from PostgreSQL and
  runs `EnsureSchema` on startup, so it comes up cleanly against an empty
  database and needs no PVC or volsync.
- **`pg push` speaks the PostgreSQL wire protocol,** not HTTP.
  Workstations therefore connect to the database directly, not through the gateway.

## Configuration

| Setting                          | Value                                                                                                            |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Image                            | `ghcr.io/kenn-io/agentsview`                                                                                     |
| Mode                             | `PG_SERVE=1` → entrypoint runs `agentsview pg serve`                                                             |
| Database                         | `agentsview` on the `datasci16` cluster                                                                          |
| Connection string                | `POSTGRES_URL` from the `database-agentsview` secret, templated in `db/postgres.yaml` to carry `sslmode=require` |
| Data dir (`AGENTSVIEW_DATA_DIR`) | `/data`, an emptyDir — holds only `config.toml`                                                                  |
| Ingress                          | `envoy-internal`, Authelia OIDC via `SecurityPolicy`                                                             |

`--public-url=https://agentsview.${SECRET_DOMAIN}` is not cosmetic.
The server validates the `Host` header on every `/api/` request against the addresses it bound to, as DNS-rebinding protection.
Requests arriving through Envoy carry the public hostname, so without this flag the UI loads but every API call returns 403.

## Client setup

Run this once per workstation.

1. Read the connection string the operator generated (it is one shared role, so
   every workstation uses the same URL):

   ```bash
   kubectl get secret database-agentsview -n datasci -o jsonpath='{.data.POSTGRES_URL}' | base64 -d
   ```

2. Point the LAN hostname at it and give the machine a stable name in `~/.agentsview/config.toml`.
   Swap the in-cluster host for `datasci-db.${SECRET_DOMAIN}` and keep `sslmode=require` — the client rejects a DSN that permits plaintext to a remote host:

   ```toml
   [pg]
   url = "postgresql://<role>:<password>@datasci-db.${SECRET_DOMAIN}:5432/agentsview?sslmode=require"
   machine_name = "hostname-you-want-in-the-ui"
   ```

   `AGENTSVIEW_PG_URL` works too if you would rather keep the URL out of the file.

3. Seed the database, then install the watcher so it stays current:

   ```bash
   agentsview pg push
   agentsview pg service install
   ```

   `agentsview pg push --watch` runs the same loop in the foreground.

## Semantic search (optional, off by default)

Text search works out of the box.
Semantic search is wired but not switched on, and needs three things.

1. The `vector` extension in the `agentsview` database.
   `pgvector` ships in the CNPG image — the `system` tag builds from the `standard` stage, which installs `postgresql-${PG_MAJOR}-pgvector`.
   But `vector` is not a trusted extension, so the `agentsview` owner role cannot create it.
   The `Postgres` CR in [db/postgres.yaml](db/postgres.yaml) asks the operator to create it, which works only if the operator connects as a role holding superuser.
   If it doesn't, the CR reports the failure and a superuser does it once by hand:

```bash
kubectl exec -n datasci "$(kubectl get pods -n datasci -l cnpg.io/instanceRole=primary -o name)" -- psql -d agentsview -c 'CREATE EXTENSION IF NOT EXISTS vector'
```

Either way nothing crashes without it: AgentsView attempts the same statement during schema setup and logs a one-line notice when it is refused.

2. `[vector]` filled in and enabled in [app/config/config.toml](app/config/config.toml).
   An init container copies that file to `/data/config.toml` on every pod start — a copy rather than a mount, because the server writes a generated auth token back into it and treats a write failure as fatal.
   Model identity must match the workstations exactly; those fields form the generation fingerprint, and a mismatch leaves the hub with no vectors it can compare against.
   Only the endpoint may differ.
   With `enabled = true` the pod refuses to start unless `model`, `dimension`, and a server are all set, so a half-filled block fails loudly instead of silently serving nothing.

3. An OpenAI-compatible embeddings endpoint the pod can reach, for encoding search queries.
   Nothing in the cluster serves one today.

## Recovering from a schema incompatibility

`pg serve` migrates the schema forward on startup, but refuses to run against one it considers incompatible — most likely after an image bump.
It exits with `pg serve: schema incompatible` and names the fix.
There is no reset subcommand; the schema is dropped by hand.

Nothing here is recoverable from PostgreSQL alone, but nothing is lost either: every workstation still holds the authoritative SQLite archive, and a full push rebuilds the hub from them.

1. Suspend the app so it stops crash-looping into a half-dropped schema:

   ```bash
   flux suspend hr agentsview -n datasci
   ```

2. Drop the schema.
   It is named `agentsview` (the `[pg] schema` default) and holds only pushed data:

   ```bash
   kubectl exec -n datasci "$(kubectl get pods -n datasci -l cnpg.io/instanceRole=primary -o name)" -- psql -d agentsview -c 'DROP SCHEMA IF EXISTS agentsview CASCADE'
   ```

3. Resume. `EnsureSchema` recreates the tables at the current version on startup:

   ```bash
   flux resume hr agentsview -n datasci
   ```

4. Repopulate from every workstation. `--full` is required — an incremental push would skip sessions it believes are already there:

   ```bash
   agentsview pg push --full
   ```

Until each machine has run step 4, the dashboard shows only the machines that have.

## Dependencies

- `cnpg-cluster-datasci` — the `datasci16` PostgreSQL cluster
- `ext-postgres-operator-datasci` — provisions the database and role from the
  `Postgres`/`PostgresUser` CRs in `db/`
- `envoy-gateway` (`envoy-internal`) and `authelia` for ingress and login
- `external-secrets` — pulls the OIDC client secret from `datasci.agentsview`

## Gotchas

- **Every workstation shares one database role.**
  The operator provisions a single owner per database, so pushes are not attributable by credential — only by the `machine` name each client sets.
- **Deletes do not propagate.**
  Removing a session locally leaves it in PostgreSQL; upstream expects manual SQL cleanup.
- **Text search needs nothing.**
  `EnsureSchema` creates `pg_trgm`, which is a trusted extension the database owner installs on its own.
- **Bumping the image can require a schema migration.** `pg serve` migrates
  forward on startup but refuses to run against a schema it considers
  incompatible; upstream's answer is to drop and recreate the schema, then
  re-push from each machine.

## References

- [Upstream repository](https://github.com/kenn-io/agentsview)
- [PostgreSQL sync](https://github.com/kenn-io/agentsview/blob/main/docs/pg-sync.md)
- [Remote access](https://github.com/kenn-io/agentsview/blob/main/docs/remote-access.md)
- [Configuration reference](https://github.com/kenn-io/agentsview/blob/main/docs/configuration.md)

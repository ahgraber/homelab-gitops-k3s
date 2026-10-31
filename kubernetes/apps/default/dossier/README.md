# [Dossier](https://github.com/AienTech/dossier)

Self-hosted, single-user job search app.
It keeps a career profile and writes tailored resumes and cover letters for each posting.

## Storage

- PostgreSQL: database `dossier` on the shared CNPG cluster.
  The app runs its migrations on start.
- `/data`: nightly backups and zipped PDFs on a VolSync-backed PVC.

## Auth

Dossier has one password and no OIDC.
It is routed through `envoy-internal` only.

1Password item `default.dossier` (homelab vault):

| Field           | Env var            | Source                                                                              |
| --------------- | ------------------ | ----------------------------------------------------------------------------------- |
| `hash-password` | `DOSSIER_PASSWORD` | `docker run --rm -it --platform linux/amd64 ghcr.io/aientech/dossier hash-password` |
| `secret`        | `DOSSIER_SECRET`   | `openssl rand -base64 32`                                                           |

Changing either value signs out every session.
Changing `DOSSIER_SECRET` also makes saved API keys unreadable.

## AI provider

Set in the app under Settings → AI provider.
Use `openai` (any OpenAI-compatible API) with base URL `https://openrouter.ai/api/v1` for OpenRouter.
A hosted provider receives the profile and documents it writes from.

## Docs

- [Installation](https://github.com/AienTech/dossier/wiki)
- [Environment variables](https://github.com/AienTech/dossier/wiki/Environment-variables)
- [SECURITY.md](https://github.com/AienTech/dossier/blob/main/SECURITY.md)

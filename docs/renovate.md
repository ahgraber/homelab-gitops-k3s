# Renovate Policy and Requirements

This document defines how Renovate is expected to operate in this repository.
It is both an introduction and a normative specification.

## What Renovate Does Here

- Detects dependency references in Kubernetes, Ansible, and Taskfile YAML.
- Creates update PRs with consistent metadata (labels, semantic commits, dashboard tracking).
- Applies safety controls (release-age delay and merge-confidence signals).
- Auto-merges only explicitly trusted low-risk updates.
- Supports custom dependency extraction for non-standard version fields.

## Requirement Language

- `MUST`: required behavior.
- `SHOULD`: strong default; deviations require clear justification in PR context.
- `MAY`: optional behavior.

## Manager and Scope Requirements

### `kubernetes` manager

- MUST scan YAML in `.taskfiles/`, `ansible/`, and `kubernetes/`.
- MUST detect container image references in Kubernetes-style manifests and related YAML.
- SHOULD be the default manager for infrastructure YAML unless a narrower manager is more correct.

### `flux` manager

- MUST scan YAML in `kubernetes/` for Flux-related dependency references.
- SHOULD be used to keep Flux-source and Flux-managed references current without manual tag edits.

### `helm-values` manager

- MUST scan YAML in `kubernetes/` for Helm values image/version references.
- SHOULD be used to update chart values files that do not appear as direct `HelmRelease` version fields.

### Custom regex managers

- MUST exist for dependency patterns not handled correctly by built-in managers.
- MUST constrain `managerFilePatterns` to repo paths that actually contain the target pattern.
- MUST include a deterministic `datasourceTemplate`.
- SHOULD include explicit versioning templates when upstream tags are non-standard.
- MUST include enough context in regex to avoid accidental cross-line or unrelated matches.
- MUST support these repository use cases:
  - Annotated `# renovate:` dependency declarations in YAML.
  - OCI refs of the form `oci://repo:tag`.
  - CloudnativePG PostgreSQL image tags.
  - Cloudflare cache tag values tied to Hugo image versions.

## Safety and Stability Requirements

- Renovate MUST default PR creation delay to `3 days` to reduce churn from immediately-retracted releases and improve merge-confidence signal quality.
- Exceptions to the global delay MAY be used only for explicitly documented, allowlist-scoped rules.
- Renovate MUST handle missing/partial release timestamps for GHCR images via `minimumReleaseAgeBehaviour=timestamp-optional`.
- Renovate MUST ignore encrypted and generated paths that should never be dependency-churn surfaces:
  - `**/*.sops.*`
  - `**/.archive/**`
  - `**/resources/**`
  - `.copier-answers.yaml`
- Renovate MUST pin container images matching `postgresql` to `<17`.

## Update and Merge Policy Requirements

- PRs MUST be separated by update type (major/minor/patch/digest) to improve review clarity.
- PRs SHOULD group tightly-coupled ecosystem components (for example Flux, Cilium, Cert-Manager) to reduce noisy single-package PR floods.
- Auto-merge MUST be allowlist-based and scoped by datasource, package matchers, and update type.
- Auto-merge SHOULD target low-risk updates first:
  - digest updates for trusted container publishers
  - minor/patch/digest updates for trusted pre-commit tooling
  - curated GitHub Actions and selected release streams
- GitHub Actions auto-merge MUST use two lanes:
  - General lane: all `github-actions` updates for `minor`/`patch`/`digest` with `minimumReleaseAge=3 days` and `ignoreTests=false`.
  - Trusted fast lane: explicitly allowlisted packages only, `minor`/`patch`/`digest`, with `minimumReleaseAge=1 minute`.
- Trusted fast lane package matching MUST use exact package names (no org-wide regex wildcards).
- Current trusted fast lane package allowlist:
  - `actions/create-github-app-token`
  - `actions/checkout`
  - `actions/labeler`
  - `renovatebot/github-action`
- Personal blog container updates for `ghcr.io/ahgraber/aimlbling-about` MAY auto-merge immediately (`minimumReleaseAge=null`) across `major`/`minor`/`patch`/`digest` to minimize CVE exposure.
- Major updates SHOULD default to review-required unless a package has explicit high-confidence policy coverage.

## PR Metadata Requirements

- Renovate PRs MUST include one update-type label: `type/major`, `type/minor`, `type/patch`, or `type/digest`.
- Renovate PRs SHOULD include datasource/manager labels when applicable (container, helm, github-action, github-release, ansible, copier, pip).
- Commit messages MUST follow semantic commit conventions and encode update intent:
  - major -> breaking semantic form
  - minor -> feature semantic form
  - patch -> fix semantic form
  - digest -> chore semantic form

## Versioning Requirements

- Non-standard upstream version formats MUST define explicit `versioning` rules.
- Custom versioning SHOULD be documented with a one-line rationale in the same PR that introduces it.
- Known non-semver ecosystems in this repo (for example `k3s` release format) MUST use dedicated regex versioning.

## Configuration Layout Rules

This section defines where new policy should go.
It does not require current files to be renamed.

- Root Renovate config (`.renovaterc.json5`) MUST stay minimal and composition-focused:
  - global toggles
  - manager enablement/scope
  - inclusion of local preset modules
- Local preset modules under `.renovate/` SHOULD be organized by concern:
  - merge policy (`automerge`, confidence, release-age overrides)
  - extraction logic (`customManagers`, custom datasources)
  - update shaping (`groups`, separation strategy)
  - metadata (`labels`, semantic commit templates)
  - constraints (`allowedVersions`, versioning overrides)
- A single preset module SHOULD own a concern; avoid duplicating the same matcher across modules unless intentionally layered.
- Any new preset module MUST be documented in this file under the relevant requirement section, not as a file inventory dump.

## Change Control Requirements

When Renovate policy changes:

1. The same PR MUST update this document with the new/changed requirement.
2. The PR description SHOULD explain risk impact (noise, safety, merge velocity, or breakage risk).
3. Policy changes MUST be validated with Renovate tooling in CI or local dev shell before merge.

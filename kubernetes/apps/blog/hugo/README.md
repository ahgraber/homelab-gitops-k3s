# [AI/MLbling-About](https://github.com/ahgraber/AIMLbling-about)

Self-hosted personal blog about AI and ML, deployed with Hugo.

## How This App Is Deployed

- `HelmRelease` uses `bjw-s/app-template` to run the blog container.
- The blog is exposed through both internal and external Envoy Gateway listeners.
- A Kyverno policy (`app/kyverno-policy.yaml`) generates a Cloudflare purge job after Deployment updates.

## Cache Busting Design

Cache busting is coordinated by a single version value in `app/helmrelease.yaml`:

- `cache.cloudflare.com/tag: &cacheTag "YYYY.MM.build"` stores the canonical release tag.
- `image.tag: *cacheTag` reuses that same value for the blog container image.
- Gateway response header `Cache-Tag: *cacheTag` applies that value to Cloudflare cache tagging.

This means image version, cache tag annotation, and response cache tag are intentionally locked together.

## Renovate Behavior

- Renovate updates `cache.cloudflare.com/tag` via the custom regex manager in `.renovate/customManagers.json5`.
- Because `image.tag` is an alias (`*cacheTag`), the image version updates automatically when the cache tag changes.
- Keep `cacheTag` as the single source of truth - Do not replace `image.tag: *cacheTag` with a hardcoded value.

## Operational Implications

- If Renovate can read new GHCR tags, one dependency update bumps both image rollout and cache tag in the same PR.
- If GHCR auth breaks for Renovate, both image and cache-tag automation stop together.
- You cannot do a cache-only tag bump without also referencing an image tag with the same value.
- The purge job uses the **previous** Deployment annotation value (`request.oldObject...`) during updates to invalidate cache entries from the prior release tag.

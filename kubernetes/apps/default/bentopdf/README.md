# [BentoPDF](https://github.com/alam00000/bentopdf)

Privacy-first, self-hosted PDF toolkit (50+ tools) — manipulation (merge/split/rotate/redact/compress/OCR)
plus full AcroForm/XFA **form filling, form creation, and flattening**.

## How it works

BentoPDF is **client-side**: the container is a static [nginx-unprivileged] site (uid `101`, port `8080`) and _all_ PDF processing runs in the visitor's browser via WebAssembly.
Files never leave the browser, so the server is effectively stateless — no PVC, no VolSync, tiny footprint.

We deploy the `bentopdf-simple` image (the self-host build: same tools as the public site, without the
marketing hero/FAQ/footer).

## Configuration

- **Image**: `ghcr.io/alam00000/bentopdf-simple`, pinned by tag + digest in `app/helmrelease.yaml`.
- **Ingress**: internal only (`envoy-internal`) at `pdf.${SECRET_DOMAIN}`.
  To expose externally, add an `envoy-external` `parentRef` (and be deliberate — it's a public tool with no built-in auth; front it with Authelia if exposed).
- **securityContext**: runs as the image's `nginx` user (uid/gid `101`) with dropped capabilities and no
  privilege escalation. `readOnlyRootFilesystem` is **disabled** — the bundled nginx entrypoint writes its
  pid to `/etc/nginx/tmp` and rewrites `/etc/nginx/conf.d/default.conf` at startup (envsubst templating,
  IPv6 disable), so a read-only rootfs makes nginx fail to start.

## Gotchas

- **WASM is loaded from the jsDelivr CDN by default.**
  Feature libraries (LibreOffice/OCR WASM, etc.) are fetched by the _browser_ at runtime, not baked into the image — so the client needs internet access.
  For a fully offline/air-gapped setup, follow upstream's `prepare-airgap.sh` to self-host the WASM bundle.
- **Cross-origin isolation**: heavy WASM features need `SharedArrayBuffer`, which requires COOP/COEP headers + a secure context.
  The image's bundled nginx config sets these automatically, and we serve over HTTPS via the internal gateway, so no extra config is needed.
- **Client-side tradeoff**: bulk OCR / large-file conversion run in the browser and are bound by browser
  memory — for server-side batch OCR or a scriptable REST API, Stirling PDF is the better fit.

## Licensing

BentoPDF is AGPL-3.0 (free for this open-source, self-hosted deployment).
A commercial license is only required for closed-source / proprietary public-facing forks.

## Links

- Upstream: <https://github.com/alam00000/bentopdf>
- Docs: <https://www.bentopdf.com/docs/self-hosting/docker>

[nginx-unprivileged]: https://hub.docker.com/r/nginxinc/nginx-unprivileged

# Container images

Each subdirectory is one image build context.
The directory name becomes the GHCR package name.
`.github/workflows/container-images.yaml` discovers the build contexts and builds them for `linux/amd64` and `linux/arm64`.

## Add an image

1. Create `containers/<name>/Containerfile`.
2. Declare one default image tag as `ARG VERSION=<tag>`.
3. Use `VERSION` in the build when the upstream source has a matching version.
4. Run the final image as a non-root user and keep the runtime stage minimal.
5. Pin base images by digest before production use.

No workflow change is required.
Pull requests build every container without pushing it.
A push to `main` publishes version, version-plus-commit, and commit tags to `ghcr.io/<owner>/<name>` with BuildKit provenance and an SBOM.
Production manifests must use the published digest because a version tag can be rebuilt.

Use the manual workflow dispatch from `main` to build one container with an optional version override.
The workflow rejects container names that can escape `containers/` and versions that are not valid Docker tags.

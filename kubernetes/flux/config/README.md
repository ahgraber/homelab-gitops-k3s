# Flux configuration

The manifests in this directory bootstrap Flux controllers and the core Git source.

## SOPS secret propagation

The bootstrap task only creates the `sops-age` secret in the `flux-system` namespace.
If additional namespaces need a copy of the Age key, manually mirror the secret (for
example with EmberStack reflector) after bootstrap before moving workload Kustomizations
out of `flux-system`.

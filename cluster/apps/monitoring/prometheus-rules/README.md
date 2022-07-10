# Prometheus Rules

Rules for resources that are created _prior to_ `monitoring` kustomization
(i.e., in `config`, `core`, or `crds`) can be deployed here to ensure order-of-operations
remains valid.

Rules for resources deployed in `apps` kustomization can (should) be deployed with the
application/service.

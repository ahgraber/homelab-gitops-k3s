# Bitwarden SDK Server

Deploys the Bitwarden SDK Server used by External Secrets Operator (ESO) Bitwarden provider.

## Purpose

- Runs `ghcr.io/external-secrets/bitwarden-sdk-server` as a standalone Helm deployment (not embedded inside the ESO chart).
- Provides an in-cluster HTTPS endpoint for ESO to call.

## TLS

- TLS is enabled in the Helm chart.
- Certificates are issued by cert-manager using a namespace-scoped CA (self-signed) and stored in the `bitwarden-tls-certs` Secret.
- ESO trusts the server via the CA bundle exposed by cert-manager in the same Secret (`ca.crt`).

## References

- Chart values: https://github.com/external-secrets/bitwarden-sdk-server/blob/main/deploy/charts/bitwarden-sdk-server/values.yaml

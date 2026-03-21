set quiet := true
set shell := ["bash", "-euo", "pipefail", "-c"]

security_dir := source_directory()
root_dir := shell('git -C "' + security_dir + '" rev-parse --show-toplevel')

[private]
default:
    just --list oauth

[group("oauth")]
[doc("Generate an OAuth client secret for an app and print the required Authelia follow-up steps")]
secret namespace app *flags:
    uv run '{{ root_dir }}/scripts/oauth_client.py' {{ namespace }} {{ app }} {{ flags }}
    @printf '\nNext steps:\n'
    @printf '1. Add the provider to kubernetes/apps/security/authelia/app/config/configuration.yaml under identity_providers.oidc.clients.\n'
    @printf '2. Add the digest data entry to kubernetes/apps/security/authelia/app/secret.externalsecret.yaml so Authelia can read the generated <APP>_OAUTH_CLIENT_DIGEST value.\n'

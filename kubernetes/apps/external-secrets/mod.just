set quiet := true
set shell := ["bash", "-euo", "pipefail", "-c"]
# Exposes recipe arguments as "$@" so field specs reach the script verbatim.
# Field labels may carry a bracketed type - 'adminUsername[text]' - and bash
# would otherwise treat the brackets as a glob pattern.
set positional-arguments := true

external_secrets_dir := source_directory()
root_dir := shell('git -C "' + external_secrets_dir + '" rev-parse --show-toplevel')

[private]
default:
    just --list secrets

[doc("List available recipes")]
list:
    just --justfile '{{ module_file() }}' --list

[group("secrets")]
[doc("Create a placeholder 1Password item ({namespace}.{app}) with fields to fill in by hand")]
create namespace app *fields:
    uv run '{{ root_dir }}/scripts/onepassword/create_item.py' "$@"

[group("secrets")]
[confirm("Force a refresh for all ExternalSecrets across the cluster?")]
[doc("Force all ExternalSecrets to refresh from their backing secret stores")]
sync:
    ts=$(date +%s); \
    kubectl get externalsecrets -A --no-headers | while read -r ns name _; do \
      kubectl annotate externalsecret "$name" force-sync="$ts" --overwrite -n "$ns"; \
    done

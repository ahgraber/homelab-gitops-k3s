set quiet := true
set shell := ["bash", "-euo", "pipefail", "-c"]

[private]
default:
    just --list secrets

[group("secrets")]
[confirm("Force a refresh for all ExternalSecrets across the cluster?")]
[doc("Force all ExternalSecrets to refresh from their backing secret stores")]
sync:
    ts=$(date +%s); \
    kubectl get externalsecrets -A --no-headers | while read -r ns name _; do \
      kubectl annotate externalsecret "$name" force-sync="$ts" --overwrite -n "$ns"; \
    done

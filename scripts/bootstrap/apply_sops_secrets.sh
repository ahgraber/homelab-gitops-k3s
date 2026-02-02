#! /usr/bin/env bash

# shellcheck source=./common.sh
source "$(dirname "${0}")/common.sh"
export LOG_LEVEL="debug"
ROOT_DIR="$(git rev-parse --show-toplevel)"
export ROOT_DIR

function apply_sops_secrets() {
    log debug "Applying secrets"

    local -r secrets=(
        "${ROOT_DIR}/bootstrap/github-deploy-key.sops.yaml"
        "${ROOT_DIR}/bootstrap/age-key.sops.yaml"
        "${ROOT_DIR}/kubernetes/components/sops/cluster-secrets.sops.yaml"
        "${ROOT_DIR}/kubernetes/components/sops/custom-secrets.sops.yaml"
        "${ROOT_DIR}/kubernetes/apps/network/cloudflared/app/secret.sops.yaml"
    )


    for secret in "${secrets[@]}"; do
        if [[ ! -f "${secret}" ]]; then
            log warn "File does not exist" "file=${secret}"
            continue
        fi

        # Check if the secret resources are up-to-date
        if sops exec-file "${secret}" "kubectl --namespace flux-system diff --filename {}" &>/dev/null; then
            log info "Secret resource is up-to-date" "resource=$(basename "${secret}" ".sops.yaml")"
            continue
        fi

        # Apply secret resources
        if sops exec-file "${secret}" "kubectl --namespace flux-system apply --server-side --filename {}" &>/dev/null; then
            log info "Secret resource applied successfully" "resource=$(basename "${secret}" ".sops.yaml")"
        else
            log error "Failed to apply secret resource" "resource=$(basename "${secret}" ".sops.yaml")"
        fi
    done
}

apply_sops_secrets

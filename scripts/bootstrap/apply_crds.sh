#! /usr/bin/env bash

# shellcheck source=./common.sh
source "$(dirname "${0}")/common.sh"
export LOG_LEVEL="debug"
ROOT_DIR="$(git rev-parse --show-toplevel)"
export ROOT_DIR

# CRDs to be applied before the helmfile charts are installed
function apply_crds() {
    log debug "Applying CRDs"

    local -r helmfile_file="${ROOT_DIR}/bootstrap/helmfile.d/00-crds.yaml"

    if [[ ! -f "${helmfile_file}" ]]; then
        log error "File does not exist" "file" "${helmfile_file}"
    fi

    if ! crds=$(helmfile --file "${helmfile_file}" template --quiet | yq eval-all --exit-status 'select(.kind == "CustomResourceDefinition")') || [[ -z "${crds}" ]]; then
        log error "Failed to render CRDs from Helmfile" "file" "${helmfile_file}"
    fi

    if echo "${crds}" | kubectl diff --filename - &>/dev/null; then
        log info "CRDs are up-to-date"
        return
    fi

    # If fails, consider running with --server-side --force-conflicts
    if ! echo "${crds}" | kubectl apply --server-side --filename - &>/dev/null; then
        log error "Failed to apply crds from Helmfile" "file" "${helmfile_file}"
    fi

    log info "CRDs applied successfully"
}

apply_crds

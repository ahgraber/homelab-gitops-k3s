#! /usr/bin/env bash

source "$(dirname "${0}")/common.sh"
export LOG_LEVEL="debug"
ROOT_DIR="$(git rev-parse --show-toplevel)"
export ROOT_DIR

function sync_helm_releases() {
    log debug "Syncing Helm releases"

    local -r helmfile_file="${ROOT_DIR}/bootstrap/helmfile.d/01-apps.yaml"

    if [[ ! -f "${helmfile_file}" ]]; then
        log error "File does not exist" "file=${helmfile_file}"
    fi

    if ! helmfile --file "${helmfile_file}" sync --hide-notes; then
        log error "Failed to sync Helm releases"
    fi

    log info "Helm releases synced successfully"
}

sync_helm_releases

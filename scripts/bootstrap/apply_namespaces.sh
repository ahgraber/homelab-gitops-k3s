#! /usr/bin/env bash

# shellcheck source-path=SCRIPTDIR
source "$(dirname "${0}")/common.sh"
export LOG_LEVEL="debug"
ROOT_DIR="$(git rev-parse --show-toplevel)"
export ROOT_DIR

function apply_namespaces() {
    log debug "Applying namespaces"

    local -r apps_dir="${ROOT_DIR}/kubernetes/apps"

    if [[ ! -d "${apps_dir}" ]]; then
        log error "Directory does not exist" "directory=${apps_dir}"
    fi

    for app in "${apps_dir}"/*/; do
        namespace=$(basename "${app}")

        # Check if the namespace resources are up-to-date
        if kubectl get namespace "${namespace}" &>/dev/null; then
            log info "Namespace resource is up-to-date" "resource=${namespace}"
            continue
        fi

        # Apply the namespace resources
        if kubectl create namespace "${namespace}" --dry-run=client --output=yaml \
            | kubectl apply --server-side --filename - &>/dev/null;
        then
            log info "Namespace resource applied" "resource=${namespace}"
        else
            log error "Failed to apply namespace resource" "resource=${namespace}"
        fi
    done
}

apply_namespaces

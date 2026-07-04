#! /usr/bin/env bash

# Description: Render bootstrap-only resources from bootstrap/resources.yaml.j2,
#   inject secret values from 1Password (op://... references), and apply them.
#   These seed the 1Password Connect token so External Secrets Operator can
#   authenticate, plus other bootstrap-time secrets, using the 1Password CLI
#   instead of SOPS.
# Usage: ./apply_bootstrap_resources.sh

# shellcheck source=./common.sh
source "$(dirname "${0}")/common.sh"
export LOG_LEVEL="debug"
ROOT_DIR="$(git rev-parse --show-toplevel)"
export ROOT_DIR

check_cli minijinja-cli op kubectl

function apply_bootstrap_resources() {
  log debug "Applying bootstrap resources"

  local -r template="${ROOT_DIR}/bootstrap/resources.yaml.j2"

  if [[ ! -f "${template}" ]]; then
    log warn "File does not exist, skipping" "file=${template}"
    return
  fi

  # Ensure the 1Password CLI is authenticated before injecting secrets
  if ! op whoami &> /dev/null; then
    log error "1Password CLI is not authenticated" \
      "hint=run 'op signin' or export OP_SERVICE_ACCOUNT_TOKEN"
  fi

  local rendered
  if ! rendered=$(minijinja-cli "${template}" | op inject); then
    log error "Failed to render bootstrap resources" "file=${template}"
  fi

  # Check if the resources are already up-to-date
  if echo "${rendered}" | kubectl diff --filename - &> /dev/null; then
    log info "Bootstrap resources are up-to-date"
    return
  fi

  if ! echo "${rendered}" | kubectl apply --server-side --filename - &> /dev/null; then
    log error "Failed to apply bootstrap resources" "file=${template}"
  fi

  log info "Bootstrap resources applied successfully"
}

apply_bootstrap_resources

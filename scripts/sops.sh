#!/usr/bin/env bash

set -o errexit
set -o pipefail

# shellcheck disable=SC2155
PROJECT_DIR=$(git rev-parse --show-toplevel)
# shellcheck disable=SC2155
SOPS_AGE_KEY_FILE="${HOME}/Library/Application Support/sops/age/keys.txt"
AGE_PUBLIC_KEY="$(grep public """${SOPS_AGE_KEY_FILE}""" | awk '{ print $NF }')"
export PROJECT_DIR SOPS_AGE_KEY_FILE AGE_PUBLIC_KEY

main() {

  # assumes files requiring substitution will be named ".yml.tmpl" or ".yaml.tmpl"
  templates=()
  while IFS='' read -r line; do templates+=("${line}"); done < <(fd ".sops.y[a]ml$" "${PROJECT_DIR}")

  echo "Encrypting: "
  for tmpl in "${templates[@]}"; do
    echo "${tmpl}"
    sops --encrypt --in-place "${tmpl}"
  done

}

_has_envar() {
  local option="${1}"
  # shellcheck disable=SC2015
  [[ "${!option}" == "" ]] && {
    _log "ERROR" "Unset variable ${option}"
    exit 1
  } || {
    _log "INFO" "Found variable '${option}' with value '${!option}'"
  }
}

validate_age() {
  _has_envar "AGE_PUBLIC_KEY"
  _has_envar "SOPS_AGE_KEY_FILE"

  if [[ ! "${AGE_PUBLIC_KEY}" =~ ^age.* ]]; then
    _log "ERROR" "BOOTSTRAP_AGE_PUBLIC_KEY does not start with age"
    exit 1
  fi

  if [[ ! -f "${SOPS_AGE_KEY_FILE}" ]]; then
    _log "ERROR" "Unable to find Age file keys.txt in ~/.config/sops/age"
    exit 1
  fi
}

_has_binary() {
  command -v "${1}" >/dev/null 2>&1 || {
    _log "ERROR" "${1} is not installed or not found in \$PATH"
    exit 1
  }
}

verify_binaries() {
  _has_binary "fd"
}

_log() {
  local type="${1}"
  local msg="${2}"
  printf "[%s] [%s] %s\n" "$(date -u)" "${type}" "${msg}"
}

validate_age
verify_binaries
main

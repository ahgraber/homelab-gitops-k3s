#!/usr/bin/env bash

set -o errexit
set -o pipefail

# shellcheck disable=SC2155
export PROJECT_DIR=$(git rev-parse --show-toplevel)

main() {

  # assumes files requiring substitution will be named ".yml.tmpl" or ".yaml.tmpl"
  templates=()
  while IFS='' read -r line; do templates+=("${line}"); done < <(fd ".y[a]ml.tmpl" "${PROJECT_DIR}")

  echo "Substituting: "
  for tmpl in "${templates[@]}"; do
    rename="${tmpl/ml.tmpl/ml}"
    [[ -f "${rename}" ]] && rm "${rename}"
    envsubst <"${tmpl}" >"${rename}"
    echo "${tmpl} --> ${rename}"
  done

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

verify_binaries
main

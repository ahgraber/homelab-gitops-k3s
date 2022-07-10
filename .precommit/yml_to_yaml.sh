#!/usr/bin/env bash

set -o errexit
set -o pipefail

# shellcheck disable=SC2155
export PROJECT_DIR=$(git rev-parse --show-toplevel)

main() {

  # assumes files requiring substitution will be named ".yml.tmpl" or ".yaml.tmpl"
  yml=()
  while IFS='' read -r line; do yml+=("${line}"); done < <(fd ".yml" "${PROJECT_DIR}")

  echo "Renaming to *.yaml: "
  for y in "${yml[@]}"; do
    echo "${y}"
    mv "${y}" "${y/yml/yaml}"
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

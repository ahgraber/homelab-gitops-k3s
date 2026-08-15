#!/usr/bin/env bash
# Description: Discover container build contexts and validate image versions.
# Usage: container-build-info.sh discover [containers-dir] [container|all]
#        container-build-info.sh version <Containerfile> [version-override]
set -euo pipefail

export LC_ALL=C

die() {
  printf 'error: %s\n' "$1" >&2
  exit 1
}

# Patterns rather than predicate functions: shellcheck's check-set-e-suppressed
# (SC2310) fires when a function is called in a condition, because set -e does
# not apply inside it. A [[ ]] test is a builtin and carries no such caveat.
readonly CONTAINER_NAME_RE='^[a-z0-9]+([._-][a-z0-9]+)*$'
readonly CONTAINER_VERSION_RE='^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$'

discover() {
  local containers_dir="${1:-containers}"
  local requested="${2:-all}"
  local containerfile name separator
  local -a containers=()

  [[ -d "${containers_dir}" ]] || die "containers directory not found: ${containers_dir}"

  if [[ "${requested}" != "all" ]]; then
    [[ "${requested}" =~ ${CONTAINER_NAME_RE} ]] || die "invalid container name: ${requested}"
    [[ -f "${containers_dir}/${requested}/Containerfile" ]] || die "container not found: ${requested}"
    containers=("${requested}")
  else
    shopt -s nullglob
    for containerfile in "${containers_dir}"/*/Containerfile; do
      name="$(basename "$(dirname "${containerfile}")")"
      [[ "${name}" =~ ${CONTAINER_NAME_RE} ]] || die "invalid container directory name: ${name}"
      containers+=("${name}")
    done
    shopt -u nullglob
  fi

  ((${#containers[@]} > 0)) || die "no container build contexts found"

  printf '['
  separator=''
  for name in "${containers[@]}"; do
    printf '%s"%s"' "${separator}" "${name}"
    separator=','
  done
  printf ']\n'
}

resolve_version() {
  local containerfile="${1:-}"
  local override="${2:-}"
  local version

  [[ -f "${containerfile}" ]] || die "Containerfile not found: ${containerfile}"

  if [[ -n "${override}" ]]; then
    version="${override}"
  else
    version="$(sed -n 's/^ARG VERSION=//p' "${containerfile}")"
  fi

  [[ "${version}" =~ ${CONTAINER_VERSION_RE} ]] || die "invalid container version: ${version:-<empty>}"
  printf '%s\n' "${version}"
}

command="${1:-}"
case "${command}" in
  discover)
    discover "${2:-containers}" "${3:-all}"
    ;;
  version)
    resolve_version "${2:-}" "${3:-}"
    ;;
  *)
    die "usage: $0 {discover|version} ..."
    ;;
esac

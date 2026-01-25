#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
export ROOT_DIR

# Log messages with different levels
function log() {
    local level="${1:-info}"
    shift

    # Define log levels with their priorities
    local -A level_priority=(
        [debug]=1
        [info]=2
        [warn]=3
        [error]=4
    )

    # Get the current log level's priority
    local current_priority=${level_priority[${level}]:-2} # Default to "info" priority

    # Get the configured log level from the environment, default to "info"
    local configured_level=${LOG_LEVEL:-info}
    local configured_priority=${level_priority[${configured_level}]:-2}

    # Skip log messages below the configured log level
    if ((current_priority < configured_priority)); then
        return
    fi

    # Define log colors
    local -A colors=(
        [debug]="\033[1m\033[38;5;63m"  # Blue
        [info]="\033[1m\033[38;5;87m"   # Cyan
        [warn]="\033[1m\033[38;5;192m"  # Yellow
        [error]="\033[1m\033[38;5;198m" # Red
    )

    # Fallback to "info" if the color for the given level is not defined
    local color="${colors[${level}]:-${colors[info]}}"
    local msg="$1"
    shift

    # Prepare additional data
    local data=
    if [[ $# -gt 0 ]]; then
        for item in "$@"; do
            if [[ "${item}" == *=* ]]; then
                data+="\033[1m\033[38;5;236m${item%%=*}=\033[0m\"${item#*=}\" "
            else
                data+="${item} "
            fi
        done
    fi

    # Determine output stream based on log level
    local output_stream="/dev/stdout"
    if [[ "${level}" == "error" ]]; then
        output_stream="/dev/stderr"
    fi

    # Print the log message
    local timestamp
    timestamp="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    printf "%s %b%s%b %s %b\n" "${timestamp}" \
        "${color}" "${level^^}" "\033[0m" "${msg}" "${data}" >"${output_stream}"

    # Exit if the log level is error
    if [[ "${level}" == "error" ]]; then
        exit 1
    fi
}

# Check if required environment variables are set
function check_env() {
    local envs=("${@}")
    local missing=()
    local values=()

    for env in "${envs[@]}"; do
        if [[ -z "${!env-}" ]]; then
            missing+=("${env}")
        else
            values+=("${env}=${!env}")
        fi
    done

    if [[ ${#missing[@]} -ne 0 ]]; then
        log error "Missing required env variables" "envs=${missing[*]}"
    fi

    log debug "Env variables are set" "envs=${values[*]}"
}

# Check if required CLI tools are installed
function check_cli() {
    local deps=("${@}")
    local missing=()

    for dep in "${deps[@]}"; do
        if ! command -v "${dep}" &>/dev/null; then
            missing+=("${dep}")
        fi
    done

    if [[ ${#missing[@]} -ne 0 ]]; then
        log error "Missing required deps" "deps=${missing[*]}"
    fi

    log debug "Deps are installed" "deps=${deps[*]}"
}

# Load Flux-style substitution variables for bootstrap Helmfile runs.
function load_bootstrap_env() {
    local -a secrets=(
        "${ROOT_DIR}/kubernetes/components/sops/cluster-secrets.sops.yaml"
        "${ROOT_DIR}/kubernetes/components/sops/custom-secrets.sops.yaml"
    )
    local -a loaded_keys=()

    for secret in "${secrets[@]}"; do
        if [[ ! -f "${secret}" ]]; then
            log warn "Secret file is missing" "file=${secret}"
            continue
        fi

        local secret_string_entries
        if secret_string_entries=$(sops --decrypt "${secret}" | yq -r '.stringData // {} | to_entries | .[] | "\(.key)=\(.value)"'); then
            while IFS='=' read -r key value; do
                [[ -z "${key}" ]] && continue
                export "${key}=${value}"
                loaded_keys+=("${key}")
            done <<< "${secret_string_entries}"
        else
            log error "Failed to read secret stringData" "file=${secret}"
        fi

        local secret_data_entries
        if secret_data_entries=$(sops --decrypt "${secret}" | yq -r '.data // {} | to_entries | .[] | "\(.key)=\(.value | @base64d)"'); then
            while IFS='=' read -r key value; do
                [[ -z "${key}" ]] && continue
                export "${key}=${value}"
                loaded_keys+=("${key}")
            done <<< "${secret_data_entries}"
        else
            log error "Failed to read secret data" "file=${secret}"
        fi
    done

    if [[ ${#loaded_keys[@]} -gt 0 ]]; then
        log debug "Bootstrap substitution variables loaded" "keys=${loaded_keys[*]}"
    else
        log warn "No bootstrap substitution variables were loaded"
    fi
}

# Ensure any ${VAR} placeholders used by bootstrap HelmReleases have values.
function check_bootstrap_placeholders() {
    local -r helmfile_file="${1}"
    local -r apps_dir="${ROOT_DIR}/kubernetes/apps"
    local -a missing=()

    if [[ ! -f "${helmfile_file}" ]]; then
        log error "File does not exist" "file=${helmfile_file}"
    fi

    if [[ ! -d "${apps_dir}" ]]; then
        log error "Apps directory does not exist" "directory=${apps_dir}"
    fi

    local releases
    if ! releases=$(yq -r '.releases[] | "\(.namespace) \(.name)"' "${helmfile_file}"); then
        log error "Failed to read Helmfile releases" "file=${helmfile_file}"
    fi

    while IFS=' ' read -r namespace name; do
        local hr_file="${apps_dir}/${namespace}/${name}/app/helmrelease.yaml"
        if [[ ! -f "${hr_file}" ]]; then
            log warn "HelmRelease file is missing" "file=${hr_file}"
            continue
        fi

        local placeholders
        placeholders=$(grep -Eo '\$\{[A-Za-z0-9_]+\}' "${hr_file}" | sort -u) || true
        if [[ -z "${placeholders}" ]]; then
            continue
        fi

        while IFS= read -r placeholder; do
            [[ -z "${placeholder}" ]] && continue
            local key="${placeholder#\${}"
            key="${key%\}}"
            if [[ -z "${!key-}" ]]; then
                missing+=("${key} (in ${hr_file})")
            fi
        done <<< "${placeholders}"
    done <<< "${releases}"

    if [[ ${#missing[@]} -gt 0 ]]; then
        log error "Missing substitution variables for bootstrap HelmReleases" \
            "missing=${missing[*]}"
    fi
}

#!/usr/bin/env bash
# Description: Find and optionally remove orphan Ceph RBD images not referenced by Kubernetes PVs.
# Usage: ./scripts/rook-rbd-orphan-cleanup.sh [--pool ceph-blockpool] [--storage-class ceph-block] [--namespace rook-ceph] [--selector app=rook-ceph-tools] [--mode dry-run|trash|rm] [--yes] [--include-non-csi]
set -Eeuo pipefail

POOL="ceph-blockpool"
STORAGE_CLASS="ceph-block"
NAMESPACE="rook-ceph"
TOOLBOX_SELECTOR="app=rook-ceph-tools"
MODE="dry-run"
ASSUME_YES="false"
INCLUDE_NON_CSI="false"

usage() {
    cat <<'EOF'
Find orphan RBD images by comparing:
  - Kubernetes PV image names for a storage class
  - Ceph RBD images in a pool

The script only considers Ceph images that are not present in Kubernetes PVs.
It then runs safety checks for each candidate before destructive actions.

Options:
  --pool <name>            RBD pool name (default: ceph-blockpool)
  --storage-class <name>   Kubernetes StorageClass name (default: ceph-block)
  --namespace <name>       Namespace containing toolbox pod (default: rook-ceph)
  --selector <label>       Label selector for toolbox pod (default: app=rook-ceph-tools)
  --mode <mode>            Action mode: dry-run | trash | rm (default: dry-run)
  --yes                    Skip interactive confirmation for trash/rm modes
  --include-non-csi        Include non-csi-vol-* images in candidate list
  -h, --help               Show this help

Examples:
  ./scripts/rook-rbd-orphan-cleanup.sh
  ./scripts/rook-rbd-orphan-cleanup.sh --mode trash --yes
  ./scripts/rook-rbd-orphan-cleanup.sh --pool ceph-blockpool --storage-class ceph-block --mode rm
EOF
}

log() {
    printf '%s\n' "$*"
}

need_cmd() {
    local cmd="$1"
    if ! command -v "${cmd}" >/dev/null 2>&1; then
        echo "Missing required command: ${cmd}" >&2
        exit 1
    fi
}

while [[ $# -gt 0 ]]; do
    case "$1" in
    --pool)
        POOL="$2"
        shift 2
        ;;
    --storage-class)
        STORAGE_CLASS="$2"
        shift 2
        ;;
    --namespace)
        NAMESPACE="$2"
        shift 2
        ;;
    --selector)
        TOOLBOX_SELECTOR="$2"
        shift 2
        ;;
    --mode)
        MODE="$2"
        shift 2
        ;;
    --yes)
        ASSUME_YES="true"
        shift
        ;;
    --include-non-csi)
        INCLUDE_NON_CSI="true"
        shift
        ;;
    -h | --help)
        usage
        exit 0
        ;;
    *)
        echo "Unknown argument: $1" >&2
        usage
        exit 1
        ;;
    esac
done

case "${MODE}" in
    dry-run | trash | rm) ;;
    *)
        echo "Invalid --mode: ${MODE} (expected: dry-run|trash|rm)" >&2
        exit 1
        ;;
esac

need_cmd kubectl
need_cmd jq
need_cmd sort
need_cmd comm
need_cmd mktemp

TOOLBOX_POD="$(kubectl get pods -n "${NAMESPACE}" -l "${TOOLBOX_SELECTOR}" -o jsonpath='{.items[0].metadata.name}')"
if [[ -z "${TOOLBOX_POD}" ]]; then
    echo "Could not find toolbox pod in namespace ${NAMESPACE} with selector ${TOOLBOX_SELECTOR}" >&2
    exit 1
fi

log "Using toolbox pod: ${TOOLBOX_POD}"
log "Pool=${POOL} StorageClass=${STORAGE_CLASS} Mode=${MODE}"

workdir="$(mktemp -d)"
trap 'rm -rf "${workdir}"' EXIT

pv_file="${workdir}/pv_images.txt"
rbd_file="${workdir}/rbd_images.txt"
orphans_file="${workdir}/orphans.txt"

kubectl get pv -o json \
    | jq -r --arg sc "${STORAGE_CLASS}" '.items[]
      | select(.spec.storageClassName == $sc)
      | .spec.csi.volumeAttributes.imageName // empty' \
    | sed '/^$/d' | sort -u >"${pv_file}"

kubectl exec -n "${NAMESPACE}" "${TOOLBOX_POD}" -- rbd ls -p "${POOL}" \
    | sed '/^$/d' | sort -u >"${rbd_file}"

comm -23 "${rbd_file}" "${pv_file}" >"${orphans_file}"

if [[ "${INCLUDE_NON_CSI}" != "true" ]]; then
    tmp="${workdir}/orphans-csi-only.txt"
    grep '^csi-vol-' "${orphans_file}" >"${tmp}" || true
    mv "${tmp}" "${orphans_file}"
fi

candidate_count="$(wc -l <"${orphans_file}" | tr -d ' ')"
log "Candidate orphan images: ${candidate_count}"

if [[ "${candidate_count}" == "0" ]]; then
    log "No orphan candidates found."
    exit 0
fi

safe_file="${workdir}/safe.txt"
skip_file="${workdir}/skipped.txt"
: >"${safe_file}"
: >"${skip_file}"

while IFS= read -r img; do
    [[ -z "${img}" ]] && continue

    if ! kubectl exec -n "${NAMESPACE}" "${TOOLBOX_POD}" -- rbd info -p "${POOL}" "${img}" >/dev/null 2>&1; then
        echo "${img}: missing_or_unreadable" >>"${skip_file}"
        continue
    fi

    status_out="$(kubectl exec -n "${NAMESPACE}" "${TOOLBOX_POD}" -- rbd status -p "${POOL}" "${img}" 2>/dev/null || true)"
    if ! grep -q 'Watchers: none' <<<"${status_out}"; then
        echo "${img}: has_watchers_or_status_unknown" >>"${skip_file}"
        continue
    fi

    snap_out="$(kubectl exec -n "${NAMESPACE}" "${TOOLBOX_POD}" -- rbd snap ls -p "${POOL}" "${img}" 2>/dev/null || true)"
    snap_lines="$(printf '%s\n' "${snap_out}" | sed '/^$/d' | wc -l | tr -d ' ')"
    if [[ "${snap_lines}" -gt 1 ]]; then
        echo "${img}: has_snapshots" >>"${skip_file}"
        continue
    fi

    children_out="$(kubectl exec -n "${NAMESPACE}" "${TOOLBOX_POD}" -- rbd children -p "${POOL}" "${img}" 2>/dev/null || true)"
    children_non_empty="$(printf '%s' "${children_out}" | sed '/^$/d')"
    if [[ -n "${children_non_empty}" ]]; then
        echo "${img}: has_children" >>"${skip_file}"
        continue
    fi

    echo "${img}" >>"${safe_file}"
done <"${orphans_file}"

safe_count="$(wc -l <"${safe_file}" | tr -d ' ')"
skip_count="$(wc -l <"${skip_file}" | tr -d ' ')"

log "Safe to act on: ${safe_count}"
log "Skipped by safety checks: ${skip_count}"

if [[ "${skip_count}" != "0" ]]; then
    log "Skipped candidates:"
    cat "${skip_file}"
fi

if [[ "${safe_count}" == "0" ]]; then
    log "No safe candidates after checks."
    exit 0
fi

log "Safe candidates:"
cat "${safe_file}"

if [[ "${MODE}" == "dry-run" ]]; then
    log "Dry-run mode: no changes made."
    exit 0
fi

if [[ "${ASSUME_YES}" != "true" ]]; then
    printf 'Proceed with mode=%s for %s images? [y/N]: ' "${MODE}" "${safe_count}"
    read -r reply
    if [[ "${reply}" != "y" && "${reply}" != "Y" ]]; then
        log "Aborted by user."
        exit 0
    fi
fi

while IFS= read -r img; do
    [[ -z "${img}" ]] && continue

    if [[ "${MODE}" == "trash" ]]; then
        log "Trashing ${img}"
        kubectl exec -n "${NAMESPACE}" "${TOOLBOX_POD}" -- rbd trash mv -p "${POOL}" "${img}"
    elif [[ "${MODE}" == "rm" ]]; then
        log "Removing ${img}"
        kubectl exec -n "${NAMESPACE}" "${TOOLBOX_POD}" -- rbd rm -p "${POOL}" "${img}"
    fi
done <"${safe_file}"

log "Completed mode=${MODE}."

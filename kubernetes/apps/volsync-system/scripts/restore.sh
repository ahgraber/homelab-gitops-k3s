#!/usr/bin/env bash
# Description: Restore a VolSync ReplicationSource from a restic snapshot.
# Usage: ./restore.sh <app> <namespace> <previous> <timestamp>
#
# Orchestrates: suspend flux ks/hr → scale down app → wipe PVC → restore → resume
set -euo pipefail

APP="${1:?Usage: restore.sh <app> <namespace> <previous> <timestamp>}"
NS="${2:-default}"
PREVIOUS="${3:-2}"
TS="${4:-$(date +%H%M%S)}"

SCRIPTS_DIR="$(cd "$(dirname "${0}")" && pwd)"
TEMPLATES_DIR="${SCRIPTS_DIR}/templates"

# Export for envsubst in templates
export app="${APP}" ns="${NS}" previous="${PREVIOUS}" ts="${TS}"

# Resolve metadata
ks=$(kubectl -n "${NS}" get replicationsource "${APP}" -o jsonpath='{.metadata.labels.kustomize\.toolkit\.fluxcd\.io/name}')
claim=$(kubectl -n "${NS}" get replicationsource "${APP}" -o jsonpath='{.spec.sourcePVC}')
app_name=$(kubectl -n "${NS}" get persistentvolumeclaim "${claim}" -o jsonpath='{.metadata.labels.app\.kubernetes\.io/name}')

if kubectl -n "${NS}" get "deployment.apps/${app_name}" >/dev/null 2>&1; then
    controller="deployment.apps/${app_name}"
else
    controller="statefulset.apps/${app_name}"
fi

# Suspend flux resources
flux -n flux-system suspend kustomization "${ks}"
flux -n "${NS}" suspend helmrelease "${APP}"

# Scale down and wait
kubectl -n "${NS}" scale "${controller}" --replicas 0
kubectl -n "${NS}" wait pod --for delete --selector="app.kubernetes.io/name=${APP}" --timeout=2m

# Wipe PVC
envsubst < "${TEMPLATES_DIR}/WipeJob.tmpl.yaml" | kubectl apply -f -
bash "${SCRIPTS_DIR}/wait-for-job.sh" "wipe-${APP}-${claim}-${TS}" "${NS}"
kubectl -n "${NS}" wait "job/wipe-${APP}-${claim}-${TS}" --for condition=complete --timeout=120m
kubectl -n "${NS}" logs "job/wipe-${APP}-${claim}-${TS}" --container wipe
kubectl -n "${NS}" delete job "wipe-${APP}-${claim}-${TS}"

# Restore from snapshot
envsubst < "${TEMPLATES_DIR}/ReplicationDestination.tmpl.yaml" | kubectl apply -f -
bash "${SCRIPTS_DIR}/wait-for-job.sh" "volsync-dst-${APP}-${claim}-${TS}" "${NS}"
kubectl -n "${NS}" wait "job/volsync-dst-${APP}-${claim}-${TS}" --for condition=complete --timeout=120m
kubectl -n "${NS}" delete replicationdestination "${APP}-${claim}-${TS}"

# Resume flux resources
flux -n "${NS}" resume helmrelease "${APP}"
flux -n flux-system resume kustomization "${ks}"

echo "Restore complete for ${APP} in ${NS}"

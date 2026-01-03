# Observability review and migration notes

## Current layout (this repository)
- Observability workloads live under `kubernetes/apps/observability/`, with Grafana, kube-prometheus-stack, VictoriaLogs, Fluent Bit, Karma, Goldilocks, node-problem-detector, nut-exporter, Scrutiny, and speedtest-exporter grouped together in a single namespace tree. Dashboards are bundled with Grafana rather than scoped per-app.
- Grafana comes from the upstream Helm chart at `kubernetes/apps/observability/grafana/app/helmrelease.yaml`; datasources for Alertmanager and Prometheus plus dashboard providers/folders (default, Ceph, Flux, Kubernetes, Nginx, Prometheus) are defined directly in values, together with OAuth and plugin settings. Dashboards are pulled from Grafana.com and monitoring-mixins URLs in the same values block, so ownership is centralized inside the HelmRelease.
- VictoriaLogs is deployed through the bjw-s app-template at `kubernetes/apps/observability/victoria-logs/app/helmrelease.yaml`, with 10d retention and a Ceph-backed PVC exposed via Envoy. The chart also enables bundled dashboards tied to the existing Grafana datasource UID.
- kube-prometheus-stack (at `kubernetes/apps/observability/kube-prometheus-stack/`) supplies Prometheus/Alertmanager and exporters. Grafana is disabled there in favor of the standalone HelmRelease above, and custom rules/relabeling live inside the stack values.

## Differences vs Grafana Operator-based approach
- Repos like onedr0p/home-ops and Diaoul/home-ops use the Grafana Operator to materialize `Grafana`/`GrafanaDatasource`/`GrafanaDashboard` resources. Dashboards typically live next to the owning app (e.g., `kubernetes/apps/<namespace>/<app>/`), while Grafana core settings stay in the Grafana app directory. This contrasts with the current centralization inside a single HelmRelease values file.
- Operator-managed folders and datasources are decoupled from Helm values, making it easier to give each app directory its own dashboards while sharing common datasources. Your current setup keeps all dashboard JSON references in one place and uses Helm-managed folders; migrating means splitting these definitions into CRs without losing the existing folder and datasource names.

## Migration suggestions (preserve existing tuning)
1. **Introduce Grafana Operator alongside Helm**
   - Add the operator to `kubernetes/apps/observability/grafana/` and mirror current Grafana settings in `Grafana`/`GrafanaDatasource` CRs (keep the `Alertmanager` and `Prometheus` datasources with the same UIDs and URLs). Preserve OAuth config, plugins, replicas, and storage choices already present in the HelmRelease values.
2. **Relocate dashboards with preserved folders**
   - Convert the HelmRelease dashboard list into `GrafanaDashboard` CRs. Place shared/infra dashboards in the Grafana app directory and co-locate app-specific dashboards (Ceph, Flux, VolSync, Kubernetes, Nginx, Prometheus) with their respective app manifests so ownership matches onedr0p/Diaoul patterns. Use folder annotations or `GrafanaFolder` CRs to keep the existing folder structure intact.
3. **Integrate monitoring.mixins.dev assets**
   - Render mixins into dashboard and rule manifests and store them with their owners (e.g., cert-manager dashboards in the cert-manager app tree, kube-state-metrics in kube-prometheus-stack). Ensure datasource variables map to your existing aliases (`Prometheus`, `alertmanager`) so no rule or dashboard needs to change targets.
4. **KEDA, VictoriaLogs, silence-operator**
   - Add KEDA as its own app with CRDs managed by Flux; point the metrics scraper at the current Prometheus endpoint and reuse your resource limits/requests to match existing sizing.
   - Keep VictoriaLogs values (10d retention, Ceph PVC, Envoy route) unchanged; if the operator ships dashboards, register them against the same datasource UID used today to avoid breaking queries.
   - Introduce silence-operator targeting the existing Alertmanager route; migrate silences declaratively while leaving kube-prometheus-stack rules intact.
5. **Transition plan**
   - Run Grafana Operator in parallel, fronted by a temporary host/path until dashboards and datasources reconcile. Once CR-based dashboards match the Helm-managed set, cut traffic over and retire the Helm-managed dashboard provisioning. Maintain current resource settings during the cutover to avoid incidental performance changes.

# Observability

This folder contains manifests and kustomizations for the cluster observability stack deployed in this repo.

Included components

- `kube-prometheus-stack/` - Prometheus, Alertmanager, PrometheusOperator, node-exporter, kube-state-metrics, ServiceMonitors and rules (via the kube-prometheus-stack Helm chart / manifests).
- `grafana/` - Grafana dashboards and configuration.
- `fluent-bit/` - DaemonSet that forwards cluster logs into the log store.
- `victoria-metrics/` - VictoriaMetrics single instance providing log and metric storage.
- `karma/` - Grafana Karma for sharing alerts and silences UI.
- `goldilocks/` - Goldilocks (Vertical Pod Autoscaler recommendations via VPA).
- `node-problem-detector/` - Daemon to detect kernel/node issues.
- `nut-exporter/` - Exporter for UPS (nut) metrics.
- `scrutiny/` - Scrutiny for SMART/disk health monitoring.
- `speedtest-exporter/` - Periodic network speed measurements exporter.
- `namespace.yaml` - Namespace manifest for the observability namespace.
- `kustomization.yaml` - Root kustomize that composes the above.

Quick notes

- The primary metrics stack is provided by `kube-prometheus-stack` (Prometheus + Alertmanager + exporters).
- Logs are collected by `fluent-bit` and stored in `victoria-metrics`, which exposes a Loki-compatible API for Grafana.
- Dashboards live in `grafana/` and are configured to read from Prometheus and VictoriaMetrics.
- `karma` provides a lightweight alerts/silences UI for Grafana alerts.
- Resource recommendation tooling: `goldilocks` (uses VPA) — check its namespace for recommendations.
- Node-level issues are surfaced by `node-problem-detector`.
- UPS and SMART monitoring: `nut-exporter` and `scrutiny` respectively.

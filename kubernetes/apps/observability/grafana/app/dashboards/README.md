# Grafana Dashboards

Platform / cross-cutting Grafana dashboards, managed as `GrafanaDashboard` CRs (grafana-operator).
This is the single home for dashboards **not** owned by a specific app.

## Convention

- **One mechanism only:** `GrafanaDashboard` CRs.
  Do **not** use sidecar-style ConfigMaps labeled `grafana_dashboard: "true"` — the operator-managed Grafana has no sidecar and will not load them.
- **Placement:**
  - _Platform / cross-cutting_ dashboards (Kubernetes, node-exporter, Prometheus,
    volumes, exporters without their own app) live **here**, grouped by category:
    - `kubernetes.yaml` — Kubernetes views/system + volumes
    - `infrastructure.yaml` — node-exporter, Prometheus
    - `exporters.yaml` — opnsense, nut, speedtest
    - `pod-resources-max.yaml` — custom in-repo dashboard
  - _App-specific_ dashboards live **with their app**:
    `apps/<namespace>/<app>/app/grafanadashboard.yaml`.
- **Standard CR fields:**
  - `instanceSelector.matchLabels.dashboards: grafana`
  - `datasources: [{ datasourceName: prometheus, inputName: DS_PROMETHEUS }]`
    (use the dashboard's actual input name — e.g. opnsense uses `DS_PROMETHEUS-K0`)
  - pin grafana.com dashboards via `url: https://grafana.com/api/dashboards/<id>/revisions/<rev>/download`
- **No vendoring:** reference upstream (grafana.com revision or upstream raw URL).
  The only in-repo JSON is `pod-resources-max.json` (a custom dashboard), loaded by its `GrafanaDashboard` via a raw GitHub URL.

## Add a dashboard

1. Add a `GrafanaDashboard` entry to the appropriate category file (or a new file).
2. If it's a new file, add it to `kustomization.yaml`.

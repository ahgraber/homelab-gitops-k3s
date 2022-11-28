# Monitoring and Observability

- [Monitoring and Observability](#monitoring-and-observability)
  - [Grafana](#grafana)
  - [Prometheus](#prometheus)
  - [Thanos](#thanos)
  - [Loki](#loki)

## Grafana

Provides dashboards.  Queries from Prometheus (or Thanos)

## Prometheus

Time-series database for metrics.
Exporters / serviceMonitors ship metrics to Prometheus.

## Thanos

Long-term storage and compaction of metrics (in an s3 bucket).  Use if Prometheus gets expensive.

## Loki

Prometheus, but for logs.
Currently not used.

# Monitoring and Observability

- [Monitoring and Observability](#monitoring-and-observability)
  - [Prometheus](#prometheus)
  - [Alertmanager](#alertmanager)
  - [Grafana](#grafana)
  - [Scrutiny](#scrutiny)

## Prometheus

Time-series database for metrics.
Exporters / serviceMonitors ship metrics to Prometheus.

## Alertmanager

Alertmanager handles alerts sent by client applications such as the Prometheus server.
It takes care of deduplicating, grouping, and routing them to the correct receiver integration such as email, PagerDuty, or OpsGenie.

## Grafana

Provides dashboards. Queries from Prometheus (or Thanos)

## Scrutiny

Monitors disk drive SMART status

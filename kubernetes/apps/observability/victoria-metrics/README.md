# VictoriaMetrics

VictoriaMetrics stores long-term metrics and provides a Loki-compatible endpoint for log ingestion.  Logs from Fluent Bit are written to the `/var/lib/victoria-metrics` data directory backed by the `ceph-block` storage class.  The instance listens on port `8428` for Prometheus-style queries and on port `3100` for Loki API requests.

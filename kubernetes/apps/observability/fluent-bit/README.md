# Fluent Bit

Fluent Bit collects Kubernetes container logs from `/var/log/containers` and forwards them to the VictoriaMetrics instance via the Loki-compatible HTTP API.  This deployment mirrors the setup used in [onedr0p/home-ops](https://github.com/onedr0p/home-ops/) but is adapted to the layout of this repository.

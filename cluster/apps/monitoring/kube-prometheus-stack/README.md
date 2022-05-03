# [kube-prometheus stack](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack#kube-prometheus-stack/)

Installs the kube-prometheus stack, a collection of Kubernetes manifests, Grafana dashboards, and
Prometheus rules combined with documentation and scripts to provide easy to operate end-to-end
Kubernetes cluster monitoring with Prometheus using the Prometheus Operator.

Prometheus is an open-source systems monitoring and alerting toolkit originally built at SoundCloud.
Prometheus collects and stores _metrics_ as time series data, i.e. metrics information
is stored with the timestamp at which it was recorded, alongside optional key-value pairs called labels.

## Installation notes

`./prometheus-rules` will need to be disable on first install due to race condition.
Once `prometheus-operator` is up and running, `./prometheus-rules` can be added back

## Included

### [Kube-State-Metrics](https://github.com/kubernetes/kube-state-metrics)

### [Node Exporter](https://github.com/prometheus/node_exporter)

### Thanos

Distributed Prometheus solutions such as Thanos and Cortex use an alternate architecture in which multiple small
Prometheus instances are deployed.

In the case of Thanos, the metrics from each Prometheus are aggregated into the common Thanos deployment,
and then those metrics are exported to a persistent store, such as S3.

This more robust architecture avoids burdening any single Prometheus instance with too many time series,
while also preserving the ability to query metrics on a global level.

## Monitoring external services

### OPNSense

Add the following to the prometheus.yaml under `additionalScrapeConfigs`:

```yaml
        additionalScrapeConfigs:
          - job_name: opnsense
            honor_timestamps: true
            static_configs:
              - targets:
                  - "opnsense.${SECRET_DOMAIN}:9100"
```

### Minio on Truenas

> Prerequisite `mc` can be installed with `brew install minio/stable/mc`
> Then configure with:
> `mc alias set truenas "https://truenas.${SECRET_DOMAIN}:9000" "${SECRET_S3_ACCESS_KEY}" "${SECRET_S3_SECRET_KEY}"`
> or admin equivalents to keys

Prometheus supports a bearer token approach to authenticate prometheus scrape requests, override the default Prometheus config with the one generated using `mc`.
To generate a Prometheus config for an alias, use `mc` (via truenas shell) as follows `mc admin prometheus generate truenas`.

Add the following to the prometheus.yaml under `additionalScrapeConfigs`:

```yaml
        additionalScrapeConfigs:
          - job_name: truenas-minio
            bearer_token: <secret>
            metrics_path: /minio/v2/metrics/node  # alternatively: metrics_path: /minio/v2/metrics/cluster
            scheme: http
            static_configs:
              - targets:
                  - "truenas.${SECRET_DOMAIN}:9000"
```

## Debugging

### high memory use / OOMkilled containers

- [Rancher docs on monitoring](https://rancher.com/docs/rancher/v2.6/en/monitoring-alerting/k)
- [Rancher docs on debugging high memory use](https://rancher.com/docs/rancher/v2.6/en/monitoring-alerting/guides/memory-usage/)
- [identifying metrics contributing to high use](https://www.robustperception.io/which-are-my-biggest-metrics)

### etcd alerts

Due to a change in alerting rules that have not yet propagated to kube-prometheus-stack,
repeated etcd alerts may be raised.  To fix, use a custom [PrometheusRule](./prometheus-rules/etcd.yaml)

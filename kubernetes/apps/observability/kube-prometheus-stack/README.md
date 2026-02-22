# [kube-prometheus stack](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack#kube-prometheus-stack/)

Installs the kube-prometheus stack, a collection of Kubernetes manifests, Grafana dashboards, and
Prometheus rules combined with documentation and scripts to provide easy to operate end-to-end
Kubernetes cluster monitoring with Prometheus using the Prometheus Operator.

Prometheus is an open-source systems monitoring and alerting toolkit originally built at SoundCloud.
Prometheus collects and stores _metrics_ as time series data, i.e. metrics information is stored with the timestamp at which it was recorded, alongside optional key-value pairs called labels.

## Installation notes

`./prometheus-rules` will need to be disable on first install due to race condition.
Once `prometheus-operator` is up and running, `./prometheus-rules` can be added back

### Naming

> As of Helm Chart `v51.*`

|     | `fullNameOverride` | `nameOverride` | `cleanPrometheusOperatorObjectNames` | `alertmanager`                                          | `prometheus`                                        | `operator`                               | `kube-state-metrics`                           |
| :-: | :----------------: | :------------: | :----------------------------------: | :------------------------------------------------------ | :-------------------------------------------------- | :--------------------------------------- | :--------------------------------------------- |
| 🆗  |       'kps'        |     `null`     |               `false`                | `alertmanager-kps-alertmanager-0`                       | `prometheus-kps-prometheus-0`                       | `kps-operator-...`                       | `kube-prometheus-stack-kube-state-metrics-...` |
| ❌  |       `null`       |     'kps'      |               `false`                | `alertmanager-kube-prometheus-stack-kps-alertmanager-0` | `prometheus-kube-prometheus-stack-kps-prometheus-0` | `kube-prometheus-stack-kps-operator-...` | `kube-prometheus-stack-kube-state-metrics-...` |
| 🆗  |       'kps'        |     'kps'      |               `false`                | `alertmanager-kps-alertmanager-0`                       | `prometheus-kps-prometheus-0`                       | `kps-operator-...`                       | `kube-prometheus-stack-kube-state-metrics-...` |
| ✅  |       'kps'        |     `null`     |                `true`                | `alertmanager-kps-0`                                    | `prometheus-kps-0`                                  | `kps-operator-...`                       | `kube-prometheus-stack-kube-state-metrics-...` |
| ❌  |       `null`       |     'kps'      |                `true`                | `alertmanager-kube-prometheus-stack-kps-0`              | `prometheus-kube-prometheus-stack-kps-0`            | `kube-prometheus-stack-kps-operator-...` | `kube-prometheus-stack-kube-state-metrics-...` |
| ✅  |       'kps'        |     'kps'      |                `true`                | `alertmanager-kps-0`                                    | `prometheus-kps-0`                                  | `kps-operator-...`                       | `kube-prometheus-stack-kube-state-metrics-...` |

|     | `fullNameOverride` | `cleanPrometheusOperatorObjectNames` | `values.kube-state-metrics.fullNameOverride` | `alertmanager`       | `prometheus`       | `operator`         | `kube-state-metrics`     |
| :-: | :----------------: | :----------------------------------: | :------------------------------------------- | :------------------- | :----------------- | :----------------- | :----------------------- |
| ⭐️  |       'kps'        |                `true`                | `kube-state-metrics`                         | `alertmanager-kps-0` | `prometheus-kps-0` | `kps-operator-...` | `kube-state-metrics-...` |

## Monitoring external services

### OPNSense

Add the following to the prometheus.yaml under `additionalScrapeConfigs`:

```yaml
additionalScrapeConfigs:
  - job_name: opnsense
    honor_timestamps: true
    static_configs:
      - targets:
          - opnsense.${SECRET_INT_DOMAIN}:9100
```

## Debugging

### high memory use / OOMkilled containers

- [Rancher docs on monitoring](https://rancher.com/docs/rancher/v2.6/en/monitoring-alerting/)
- [Rancher docs on debugging high memory use](https://rancher.com/docs/rancher/v2.6/en/monitoring-alerting/guides/memory-usage/)
- [identifying metrics contributing to high use](https://www.robustperception.io/which-are-my-biggest-metrics)

### Remove metric

To remove a metric (e.g., in the case that it causes a warning that does not time out), run:

```sh
# this will delete ALL metrics associated with <METRIC_NAME>
curl -X POST -g "https://prometheus.${SECRET_DOMAIN}/api/v1/admin/tsdb/delete_series?match[]=<METRIC_NAME>"
```

To target a metric associated with a particular scrape job:

```sh
# this will delete metrics associated with <METRIC_NAME> coming from <SCRAPE_JOB>
curl -X POST -g "https://prometheus.${SECRET_DOMAIN}/api/v1/admin/tsdb/delete_series?match[]=<METRIC_NAME>{job='<SCRAPE_JOB>'}"
```

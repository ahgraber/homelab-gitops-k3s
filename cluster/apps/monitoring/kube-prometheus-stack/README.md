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

## etcd alerts

Due to a change in alerting rules that have not yet propagated to kube-prometheus-stack,
repeated etcd alerts may be raised.  To fix, manually apply the custom PrometheusRule:

```sh
kubectl apply -f ./prometheus-rules/etcd.yaml
```

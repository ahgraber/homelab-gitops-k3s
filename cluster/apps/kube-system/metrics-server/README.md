# [Metrics Server](https://github.com/kubernetes-sigs/metrics-server)

Metrics Server is a scalable, efficient source of container resource metrics for
Kubernetes built-in autoscaling pipelines.

Metrics Server collects resource metrics from Kubelets and exposes them in Kubernetes apiserver
through Metrics API for use by Horizontal Pod Autoscaler and Vertical Pod Autoscaler.
Metrics API can also be accessed by kubectl top, making it easier to debug autoscaling pipelines.

Metrics Server is not meant for non-autoscaling purposes.
For example, don't use it to forward metrics to monitoring solutions,
or as a source of monitoring solution metrics.
In such cases please collect metrics from Kubelet /metrics/resource endpoint directly.

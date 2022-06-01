# Goldilocks

Get resource requests "just right".

[Goldilocks](https://github.com/FairwindsOps/goldilocks) is a utility that can help you identify a starting point for resource requests and limits

## Label namespaces

```yaml
metadata:
  ...
  labels:
    goldilocks.fairwinds.com/enabled: "true"
```

## Setting Resources

Throttling of the CPU may occur if CPU limits are placed [ref](https://github.com/robusta-dev/alert-explanations/wiki/CPUThrottlingHigh-(Prometheus-Alert)#why-cpu-throttling-can-occur-despite-low-cpu-usage-permalink).
Additionally, setting limits does not affect other containers/pods -- even if you remove this pod's CPU limit,
_other pods are still guaranteed the CPU they **request**_

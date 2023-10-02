# [reloader](https://github.com/stakater/Reloader)

A Kubernetes controller to watch changes in ConfigMap and Secrets
and do rolling upgrades on Pods with their associated Deployment, StatefulSet, DaemonSet and DeploymentConfig

## Problem

We would like to watch if some change happens in ConfigMap and/or Secret; then perform a rolling upgrade on relevant DeploymentConfig, Deployment, Daemonset, Statefulset and Rollout

## Solution

Reloader can watch changes in ConfigMap and Secret and do rolling upgrades on Pods with their associated DeploymentConfigs, Deployments, Daemonsets Statefulsets and Rollouts.

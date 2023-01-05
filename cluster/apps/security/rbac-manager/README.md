# RBAC-Manager

[RBAC Manager](https://rbac-manager.docs.fairwinds.com/introduction/) is designed to simplify
authorization in Kubernetes. This is an operator that supports declarative configuration for
RBAC with new custom resources. Instead of managing role bindings or service accounts directly,
you can specify a desired state and RBAC Manager will make the necessary changes to achieve that state

## RBAC Lookup

[RBAC Lookup](https://rbac-lookup.docs.fairwinds.com/) is a CLI that allows you to easily find
Kubernetes roles and cluster roles bound to any user, service account, or group name.
Binaries are generated with goreleaser for each release for simple installation.

```sh
brew install FairwindsOps/tap/rbac-lookup
```

# Dashboard

## Service Account token

Dashboard uses role-based account control (RBAC) to determine whether and how users can access resources. This means that the recommended way to log in is to use a Service Account token.

<!-- ```sh
# Create Service Account
NAMESPACE=monitoring  # kube-system
kubectl -n ${NAMESPACE} create serviceaccount dashboard-admin
# Give admin rights to account (automatically created by Helm chart)
kubectl create clusterrolebinding dashboard-admin --serviceaccount=${NAMESPACE}:dashboard-admin --clusterrole=cluster-admin
unset NAMESPACE
``` -->

```sh
NAMESPACE=monitoring  # kube-system
kubectl -n ${NAMESPACE} describe secret dashboard-admin-token | grep '^token' | awk '{ print $2 }'
unset NAMESPACE
```

## OpenID Connect (OIDC/OAuth2)

Providers like Authentik (or Keycloak, Dex, etc) can be used to provide an authentication flow without requiring the RBAC token.  See [authentik](../../security/authentik/README.md) for additional information.

# Headlamp

## Service Account token

Headlamp uses RBAC for checking whether and how users can access resources. This means that the recommended way to log in into Headlamp is to use a Service Account token.

```sh
# Create Service Account
NAMESPACE=monitoring  # kube-system
kubectl -n ${NAMESPACE} create serviceaccount headlamp-admin
# Give admin rights to account (automatically created by Helm chart)
kubectl create clusterrolebinding headlamp-admin --serviceaccount=${NAMESPACE}:headlamp-admin --clusterrole=cluster-admin
# Get the Secret name
SECRETNAME=$(kubectl -n ${NAMESPACE} get secrets | grep headlamp-admin | awk '{print $1}')
# Get the Token
kubectl -n ${NAMESPACE} describe secret ${SECRETNAME}
unset NAMESPACE
```

## [OpenID Connect](https://kinvolk.io/docs/headlamp/latest/installation/in-cluster/oidc/)

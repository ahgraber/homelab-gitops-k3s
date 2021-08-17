# Headlamp

## Service Account token

Headlamp uses RBAC for checking whether and how users can access resources. This means that the recommended way to log in into Headlamp is to use a Service Account token.

```sh
# Create Service Account
kubectl -n kube-system create serviceaccount headlamp-admin
# Give admin rights to account (automatically created by Helm chart)
# kubectl create clusterrolebinding headlamp-admin --serviceaccount=kube-system:headlamp-admin --clusterrole=cluster-admin
# Get the Secret name
SECRETNAME=$(kubectl -n kube-system get secrets | grep headlamp-admin | awk '{print $1}')
# Get the Token
kubectl -n kube-system describe secret ${SECRETNAME}
```

## [OpenID Connect](https://kinvolk.io/docs/headlamp/latest/installation/in-cluster/oidc/)

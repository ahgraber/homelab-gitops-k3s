# Dashboard

## Service Account token

Dashboard uses role-based account control (RBAC) to determine whether and how users can access
resources. This means that the recommended way to log in is to use a Service Account token.

<!-- ```sh
# Create Service Account
NAMESPACE=monitoring  # kube-system
kubectl -n ${NAMESPACE} create serviceaccount dashboard-admin
# Give admin rights to account (automatically created by Helm chart)
kubectl create clusterrolebinding dashboard-admin --serviceaccount=${NAMESPACE}:dashboard-admin --clusterrole=cluster-admin
unset NAMESPACE
``` -->

```sh
namespace=monitoring  # kube-system
kubectl -n ${namespace} describe secret dashboard-admin-token | grep '^token' | awk '{ print $2 }'
unset namespace
```

or alias with

```sh
dashboard-token() {
    echo "$(kubectl describe secret dashboard-admin-token -n monitoring | grep '^token' | awk '{ print $2 }')"
}
alias dbt='dashboard-token | pbcopy; echo "Copied to clipboard"'
# assuming you have `pbcopy`, this will copy to clipboard
```

## OpenID Connect (OIDC/OAuth2)

[Authorization header](https://github.com/kubernetes/dashboard/blob/master/docs/user/access-control/README.md#authorization-header)

[K8s SSO with OIDC](https://medium.com/@hbceylan/deep-dive-kubernetes-single-sign-on-sso-with-openid-connection-via-g-suite-a4f01bd4a48f)

Providers like Authentik (or Keycloak, Dex, etc) can be used to provide an authentication flow
without requiring the RBAC token. See [authentik](../../security/authentik/README.md)
or [keycloak](../../security/keycloak/README.md) for additional
information.

### Verify OIDC Token

Fill out the variables below, then copy the encoded output, open [jwt.io](https://jwt.io#debugger-io)
and paste it into the left box. On the right side you should find the decoded JSON output

```sh
KEYCLOAK_DOMAIN="keycloak.${SECRET_DOMAIN}"
KEYCLOAK_REALM="${SECRET_KEYCLOAK_REALM}"
KEYCLOAK_USERNAME="admin"
KEYCLOAK_PASSWORD="${SECRET_DEFAULT_PASSWORD}"
KEYCLOAK_CLIENT_ID="kubernetes"
KEYCLOAK_CLIENT_SECRET="${SECRET_KEYCLOAK_CLIENT_SECRET}"  # From Keycloak Client

curl -s \
-d "client_id=$KEYCLOAK_CLIENT_ID" \
-d "client_secret=$KEYCLOAK_CLIENT_SECRET" \
-d "username=$KEYCLOAK_USERNAME" \
-d "password=$KEYCLOAK_PASSWORD" \
-d "grant_type=password" \
"https://$KEYCLOAK_DOMAIN/auth/realms/$KEYCLOAK_REALM/protocol/openid-connect/token" | jq -r '.access_token'
```

### Prerequisites

1. RBAC-manager
2. [oauth2-proxy sidecar](https://www.reddit.com/r/kubernetes/comments/nk0mss/kubernetes_dashboard_with_keycloak/gzb1o1t/)

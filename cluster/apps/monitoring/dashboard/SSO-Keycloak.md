# Single Sign-On with Keycloak

## Keycloak configuration

Assuming that you already configured Keycloak for identity brokering or identity source,
let's configure it for our Dashboard!

1. Create a new client for the Kubernetes cluster.
   K8s-dashboard relies on the kube api-server for integration with OIDC auth

2. Add a new mapper in "Mappers" for the new `groups` scope. The client role (Keycloak) will map to k8s groups.
   The new mapper should have these settings:
   - Name: `groups`
   - Mapper type: `User Client Role`
   - Client ID: `<client id in keycloak>`
   - Client Role Prefix: '' # blank
   - Multivalued: `ON`
   - Token claim name: `groups`
   - Claim JSON Type: `string`
   - Add to ID token: `ON`
   - Add to access token: `ON`
   - Add to userinfo: `ON`

3. Add a new `client` for the oauth2-proxy. Use these settings:
   - Client-protocol: `openid-connect`
   - Access type: `confidential`
   - Valid redirect URIs: `https://<oauth2-host>/oauth2/callback` (where `<oauth2-host>` is the
     oauth2-proxy public FQDN)
   - In "Client Scopes", assign `groups` scope to the client
   - In "Credentials", use "Client Id and Secret", generate a new secret (if there is none) and take
     note of it

Keycloak is now ready to provide the service for oauth2 :-)

## Cluster configuration

The Kubernetes API has different security configurations for both authentication and authorization.
We'll see how to use OIDC token authentication and RBAC authorization. The former will allow us to
use Keycloak as Identity provider for Kubernetes API, while we'll use the latter to specify "which
group has access to what" (the "group" from Keycloak will be our "role" in the Kubernetes cluster).

### OIDC Authentication

First, we need to tell the Kubernetes cluster to accept OIDC tokens from our Keycloak installation ([ref](https://kubernetes.io/docs/reference/access-authn-authz/authentication/#openid-connect-tokens)).
The kubernetes api-server allows the integration of 3rd party OIDC providers -- `apiserver` must be
configured to allow/trust.

`k3s` bundles `api-server` into the `server` agent. Arguments to configure `api-server` can be passed
using `--kube-apiserver-arg` command line flags
[per ref](https://rancher.com/docs/k3s/latest/en/installation/install-options/server-config/) or
cluster leader config file at `/etc/rancher/k3s/config.yaml`:

```yaml
# add to k3s.yaml config file
# note: oidc server does NOT have to be up to launch k3s
kube-apiserver-arg:
  - "oidc-issuer-url=https://keycloak.{SECRET_DOMAIN}/auth/realms/<MY REALM>"
  - "oidc-client-id=<CLIENT NAME IN KEYCLOAK>"
  - "oidc-username-claim=email"
  - "oidc-groups-claim=groups"  # name of the mapper in Keycloak
  - "oidc-groups-prefix=oidc:"
  # - "oidc-ca-file=/etc/kubernetes/ssl/kc-ca.pem"
  #                 /etc/kubernetes/ca-bundle.crt
  #                 /var/lib/rancher/k3s/server/tls/server-ca.crt
  #                 /var/lib/rancher/k3s/server/tls/client-ca.crt
```

Check the config has been updated on each server node:

```sh
cat /etc/rancher/k3s/config.yaml
```

## Authentication Proxy

Kubernetes does not natively process authorization/authentication tokens;
the kube api-server can be configure to trust a (single!) OIDC provider,
and permit access based on bearer tokens from said provider.

Therefore, we need a middleman to determine if the user is authorized, and then pass the auth to the cluster.

### OAuth2-proxy

OAuth2-proxy is a reverse proxy and static file server that provides authentication
using Providers (Google, GitHub, and others) to validate accounts by email, domain or group.

## RBAC Authorization

In Kubernetes RBAC, there are two different kinds of rulesets: Role and ClusterRole. Role is used to
indicate a set of (additive-only) permissions in a namespace; ClusterRole is a set of permissions
for the whole cluster (for example, listing namespaces is in ClusterRole).

To assign one or more Role or ClusterRole to users and groups, Kubernetes uses RoleBinding and
ClusterRoleBinding objects.

You can find roles documentation and example in the official Kubernetes documentation for RBAC.

Assuming that you started the server using RBAC, you can assign cluster roles to OIDC groups as
follows:

```yaml
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: dashboard-admin
  namespace: monitoring
---
kind: ClusterRoleBinding
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: dashboard-admin
  namespace: monitoring
roleRef:
  kind: ClusterRole
  name: cluster-admin
  apiGroup: ""
subjects:
  # for token login
  - kind: ServiceAccount
    name: dashboard-admin
    namespace: monitoring
  # for SSO login with OIDC
  - kind: Group
    name: /admin
```

### Testing access with kubectl

```sh
kubectl config set-credentials USER_NAME \
   --auth-provider=oidc \
   --auth-provider-arg=idp-issuer-url="https://keycloak.${SECRET_DOMAIN}/auth/realms/${SECRET_KEYCLOAK_REALM}" \
   --auth-provider-arg=client-id="kubernetes" \
   --auth-provider-arg=client-secret="${SECRET_KEYCLOAK_CLIENT_SECRET}" \
   --auth-provider-arg=refresh-token=( your refresh token ) \
   --auth-provider-arg=idp-certificate-authority=( path to your ca certificate ) \
   --auth-provider-arg=id-token=( your id_token )
```

## References

- <https://www.enricobassetti.it/2021/04/protect-kubernetes-dashboard-using-oauth2-proxy-and-keycloak/>
- <https://stackoverflow.com/questions/69102035/oauth2-proxy-and-traefik-too-many-redirect> -->
  <https://github.com/codeaprendiz/devops-essentials/tree/main/kubernetes/aws/task-004-oauth2-proxy>
- <https://geek-cookbook.funkypenguin.co.nz/ha-docker-swarm/traefik-forward-auth/keycloak/>
- <https://github.com/stevegroom/traefikGateway/blob/master/traefik/docker-compose.yaml>
- <https://oleg-pershin.medium.com/kubernetes-from-scratch-oidc-and-api-server-f3af0d84c4dc>

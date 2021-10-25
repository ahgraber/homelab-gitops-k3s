# Keycloak

refs:
* https://www.enricobassetti.it/2021/04/protect-kubernetes-dashboard-using-oauth2-proxy-and-keycloak/
* https://stackoverflow.com/questions/69102035/oauth2-proxy-and-traefik-too-many-redirect --> https://github.com/codeaprendiz/devops-essentials/tree/main/kubernetes/aws/task-004-oauth2-proxy
* https://geek-cookbook.funkypenguin.co.nz/ha-docker-swarm/traefik-forward-auth/keycloak/

## Keycloak configuration

Assuming that you already configured Keycloak for identity brokering or identity source. Let’s configure it for our Dashboard!

1. Create a new scope in “Client scopes”. Name it groups (you can use a custom name, remember to change it in the rest of the config). This name will be a new openid-connect protocol client scope.
2. Add a new mapper in “Mappers” for the new groups scope. The new mapper should have these settings:
   * Name: `groups`
   * Mapper type: `Group Membership`
   * Token claim name: `groups`
   * Full group path:
     * `ON` if you want to address groups using the full path in Keycloak (e.g. /biggergroup/smallergroup)
     * `OFF` if you want to use the plain group name only
   * Add to ID token: `ON`
   * Add to access token: `ON`
   * Add to userinfo: `ON`
3. Add a new client for the oauth2-proxy. Use these settings:
   * Client-protocol: `openid-connect`
   * Access type: `confidential`
   * Valid redirect URIs: `https://<oauth2-host>/oauth2/callback` (where <oauth2-host> is the oauth2-proxy public FQDN)
   * In “Client Scopes”, assign `groups` scope to the client
   * In “Credentials”, use “Client Id and Secret”, generate a new secret (if there is none) and take note of it

Keycloak is now ready to provide the service for oauth2 :-)

## Cluster configuration

The Kubernetes API has different security configurations for both authentication and authorization. We’ll see how to use OIDC token authentication and RBAC authorization. The former will allow us to use Keycloak as Identity provider for Kubernetes API, while we’ll use the latter to specify “which group has access to what” (the “group” from Keycloak will be our “role” in the Kubernetes cluster).

### OIDC Authentication

First, we need to tell the Kubernetes cluster to accept OIDC tokens from our Keycloak installation. To do so, `apiserver` must be started using the following options:

> This is the base URL for the realm
> e.g. if the realm is "test1", the URL will be http://keycloak-server/auth/realms/test1
> `--oidc-issuer-url=https://keycloak-server/auth/realms/test1`
>
> This is the client ID provided by the OIDC provider
> `--oidc-client-id=kubernetes`
>
> If the OIDC provider is using a certificate signed by an internal authority, use this option to inject the CA certificate
> `--oidc-ca-file=/etc/kubernetes/ssl/dex-ca.pem`
>
> This is the claim used for identifying the user inside Kubernetes
> Note that everything except email claim will be considered only if they have a prefix (see below)
> `--oidc-username-claim=email`
>
> Prefix (inside the Kubernetes cluster) for the claim above
> `--oidc-username-prefix=oidc:`
>
> Group claim settings (same as the username claim, but for groups)
> `--oidc-groups-claim=groups`
> `--oidc-groups-prefix=oidc:`

```sh
# The ExecStart command should be something like:
ExecStart=/usr/local/bin/k3s \
    server \
        '--kube-apiserver-arg' \
        'oidc-issuer-url=https://keycloak.${SECRET_DOMAIN}/auth/realms/${SECRET_DOMAIN}' \
        '--kube-apiserver-arg' \
        'oidc-client-id=...' \
        '--kube-apiserver-arg' \
        'oidc-username-claim=...' \
```

### RBAC Authorization

In Kubernetes RBAC, there are two different kinds of rulesets: Role and ClusterRole. Role is used to indicate a set of (additive-only) permissions in a namespace; ClusterRole is a set of permissions for the whole cluster (for example, listing namespaces is in ClusterRole).

To assign one or more Role or ClusterRole to users and groups, Kubernetes uses RoleBinding and ClusterRoleBinding objects.

You can find roles documentation and example in the official Kubernetes documentation for RBAC.

Assuming that you started the server using RBAC, you can assign cluster roles to OIDC groups as follow:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  namespace: default
  name: read-namespaces
roleRef:
  kind: ClusterRole
  name: list-namespaces
  apiGroup: rbac.authorization.k8s.io
subjects:
- kind: Group
  name: oidc:Group1
  apiGroup: rbac.authorization.k8s.io
```

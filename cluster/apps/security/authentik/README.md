# Authentik

Authentik is an open-source Identity Provider focused on flexibility and versatility.

## Installation

See [helm-release](helm-release.yaml)
Once running, access the admin page at <https://auth.${SECRET_DOMAIN}/if/flow/initial-setup/>

## Configuration

### Identities

To use Authentik as an Identity Provider (IdP), we must have identities.
Identities (i.e., end users) can be configured in

```txt
`Identity & Cryptography`
  └ `Users`
  └ `Groups`
```

### Permissions

Authentik must be aware of end applications/services to provide access. **Applications** can be
configured in

```txt
`Applications`
  └ `Applications`
```

Applications require a **Provider** to manage the authentication/authorization.

## OIDC Auth with k3s (SSO with Kubernetes Dashboard)

### Configure k3s to use OIDC

The kubernetes api-server allows the integration of 3rd party OIDC providers. k3s bundles
`api-server` into the `server` agent. Arguments to configure `api-server` can be passed using
`--kube-apiserver-arg` command line flags
[per ref](https://rancher.com/docs/k3s/latest/en/installation/install-options/server-config/) or
cluster leader config file at `/etc/rancher/k3s/config.yaml`:

```yaml
# add to k3s.yaml config file
# note: oidc server does NOT have to be up to launch k3s
kube-apiserver-arg:
  - "oidc-issuer-url=https://auth.{SECRET_DOMAIN}"
  - "oidc-client-id=<APPLICATION_NAME_FOR_AUTHENTIK>"
  - "oidc-username-claim=email"
  - "oidc-groups-claim=groups"
```

Check the config has been updated on each server node:

```sh
cat /etc/rancher/k3s/config.yaml
```

### Log in to k8s-dashboard via Authentik as OIDC provider

1. Log in to Authentik admin page
2. In `Identity & Cryptography`, create `Users` and `Group(s)` to provide access
   1. `Group(s)` must align with the group name associated with the ClusterRole that provides
      permissions (see [RBAC](../../monitoring/dashboard/rbac.yaml))
3. In `Resources > Providers`, create a new OIDC/OAuth2 Provider
   1. Ensure provider's `client id` matches the client id passed to kube-apiserver
4. In `Resources > Applications`, create a new Application and use the associated Provider created
   above
5. In the new Application, choose an appropriate policy (i.e., users in the specific group are
   authorized)

## Proxy / ForwardAuth for other services

Ref:

<!-- markdownlint-disable MD034 -->
- https://inmanturbo.github.io/labs/truenas/apps/authentik/zero-to-auth/
- https://docs.google.com/document/d/10Zk8odxH52TiTcbcjWuCZAW9xeudZAtDVWyRFhLD6X4/edit
- https://github.com/sleighzy/k3s-traefik-forward-auth-openid-connect
- https://homelab.blog/blog/devops/Istio-OIDC-Config/
- https://github.com/oauth2-proxy/oauth2-proxy/issues/1355
- https://github.com/oauth2-proxy/oauth2-proxy/issues/46#issuecomment-502144577
<!-- markdownlint-enable MD034 -->

## Cloudflare Tunnel

[config file](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/tunnel-guide/local/local-management/configuration-file/)

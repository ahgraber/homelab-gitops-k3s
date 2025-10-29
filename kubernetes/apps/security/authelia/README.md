# [Authelia](https://github.com/authelia/authelia)

Authelia is an open-source authentication and authorization server providing two-factor authentication and single sign-on (SSO) for your applications via a web portal. It acts as a companion for reverse proxies by allowing, denying, or redirecting requests.

## Configuration Notes

### LLDAP Integration

Authelia is configured to use LLDAP for its source of truth.

1. Create an `authelia` user account in LLDAP
2. Set group for `authelia` user:
   1. By default, use `lldap_strict_readonly` permission
   2. If you are configuring Authelia to change user passwords, then use `lldap_password_manager` permission

Refer to [lldap/example_configs/authelia.md at main · lldap/lldap](https://github.com/lldap/lldap/blob/main/example_configs/authelia.md)

### Client Integration

Client integration requires configuration of Authelia and the client application (and perhaps also LLDAP if additional roles are required).

1. Update `identity_providers.oidc.clients` in Authelia's `configuration.yml`
   1. Authelia will use the hash of the client secret (`uv run scripts/authelia_hash.py`).
2. Update the application to point to Authelia as the auth provider and ensure the application knows the actual secret that we hashed for Authelia.

### Envoy-Gateway Integration

> For use if/when the application itself does not support OAUTH/OIDC

- [Envoy Gateway | Integration | Authelia](https://www.authelia.com/integration/kubernetes/envoy/gateway/) - Instructions on how to use Envoy Gateway as an external authorization filter
- [Envoy Gateway | OpenID Connect 1.0 | Integration](https://www.authelia.com/integration/openid-connect/clients/envoy-gateway/) - via Authelia `configuration.yml` or by HTTPRoute

### Generating Secrets

For all 32-byte base64 secrets (like session secret, storage encryption key):

```bash
openssl rand -hex 64
```

For RSA private key (like JWKS key), the following will create public/private .pem files in your working directory:

```bash
openssl genrsa -out private.pem 2048
openssl rsa -in private.pem -outform PEM -pubout -out public.pem
```

For client password / digest hash, create a long random password and PBKDF2-SHA512 hash
(the hash/digest is provided to Authelia; the password is used by the app):

```bash
uv run scripts/authelia_hash.py
```

### Kyverno Policy

The Kyverno policy generates a new session secret every time authelia redeploys, invalidating existing sessions and preventing the invalid cookies from causing users auth problems.

## References

- [How do I generate a client identifier or client secret? | FAQ | Authelia](https://www.authelia.com/integration/openid-connect/frequently-asked-questions/#how-do-i-generate-a-client-identifier-or-client-secret)
- [OpenID Connect 1.0 Clients | Configuration | Authelia](https://www.authelia.com/configuration/identity-providers/openid-connect/clients/)
- [OpenID Connect with Authelia on Kubernetes · Stonegarden](https://blog.stonegarden.dev/articles/2025/06/authelia-oidc/)

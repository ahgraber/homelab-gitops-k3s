# [Authelia](https://github.com/authelia/authelia)

Authelia is an open-source authentication and authorization server providing two-factor authentication and single sign-on (SSO) for your applications via a web portal. It acts as a companion for reverse proxies by allowing, denying, or redirecting requests.

## Required Secrets

Populate at least the following keys in `secret.sops.yaml`:

### Authentication & Session Secrets

- **`AUTHELIA_JWT_SECRET`** – Used to sign JWT tokens for session management. Authelia uses this to create tamper-proof session tokens.

  - Generate: `openssl rand -hex 64`

- **`AUTHELIA_SESSION_SECRET`** – Encrypts session data stored on the server side (Redis, in-memory, or database).

  - Generate: `openssl rand -hex 64`

### Storage Encryption

- **`AUTHELIA_STORAGE_ENCRYPTION_KEY`** – Master encryption key for sensitive data stored in the backend database (user preferences, TOTP secrets, etc.).
  - Generate: `openssl rand -hex 64`

### LDAP Configuration

- **`AUTHELIA_LDAP_BASE_DN`** – The LDAP Distinguished Name (DN) for your directory tree (e.g., `dc=example,dc=com`).

  - Set to your LDAP server's base DN.

- **`AUTHELIA_LDAP_ADMIN_PASSWORD`** – Password for the LDAP admin user specified in `configmap.yaml`.

  - Set to your LDAP admin user's password.

### Optional OIDC Support

Optional keys for OIDC support are commented out in both the ConfigMap and Secret template:

- **`AUTHELIA_OIDC_HMAC_SECRET`** – HMAC secret for signing OpenID Connect tokens (if enabling OIDC as an identity provider).

  - Generate: `openssl rand -hex 64`

- **`AUTHELIA_OIDC_JWKS_KEY`** – RSA private key for signing OpenID Connect ID tokens.

  - Generate: `openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048`

## Generating Secrets

To generate random secrets safely:

```bash
# For all 32-byte base64 secrets
openssl rand -hex 64

# For RSA private key (if using OIDC)
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048
```

## Setup Instructions

1. Copy `app/secret.sops.yaml.tmpl` to `app/secret.sops.yaml` (or edit the encrypted file directly)
2. Generate and populate each required secret using the commands above
3. Fill in `AUTHELIA_LDAP_BASE_DN` and `AUTHELIA_LDAP_ADMIN_PASSWORD` with your LDAP credentials
4. Encrypt the secret file: `sops --encrypt --in-place app/secret.sops.yaml`
5. Commit the encrypted file to Git – Flux will decrypt it at runtime using your age key

> **Tip:** Ensure your `age.key` is properly configured in your repository before encrypting secrets, or they won't decrypt at runtime.

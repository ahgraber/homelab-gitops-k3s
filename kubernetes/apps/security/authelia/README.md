# [Authelia](https://github.com/authelia/authelia)

Authelia is an open-source authentication and authorization server providing two-factor authentication and single sign-on (SSO) for your applications via a web portal. It acts as a companion for reverse proxies by allowing, denying, or redirecting requests.

## Generating Secrets

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
(the hash/digest is provided to authelia; the password is used by the app):

```bash
uv run scripts/authelia_hash.py
```

## Setup Instructions

1. Copy `app/secret.sops.yaml.tmpl` to `app/secret.sops.yaml` (or edit the encrypted file directly)
2. Generate and populate each required secret using the commands above
3. Fill in `AUTHELIA_LDAP_BASE_DN` and `AUTHELIA_LDAP_ADMIN_PASSWORD` with your LDAP credentials
4. Encrypt the secret file: `sops --encrypt --in-place app/secret.sops.yaml`
5. Commit the encrypted file to Git – Flux will decrypt it at runtime using your age key

> **Tip:** Ensure your `age.key` is properly configured in your repository before encrypting secrets, or they won't decrypt at runtime.

# Loginapp

Loginapp is a Web application for Kubernetes CLI configuration with OIDC.

## Prerequisites

Loginapp requires a preexisting token for config.secret or LOGINAPP_SECRET.  Generate with

```sh
openssl rand -base64 36
```

Loginapp simply links an existing OIDC/OAuth provider and provides a link to the appropriate configuration.
See [Loginapp documentation](https://github.com/fydrah/loginapp/blob/master/docs/deploy.md) for Identity Provider hints.

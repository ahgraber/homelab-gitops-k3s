# [lldap](https://github.com/lldap/lldap)

A lightweight authentication server that provides an opinionated, _simplified LDAP interface for authentication_ - LLDAP does not provide a full LDAP server. It comes with a frontend that makes user management easy, and allows users to edit their own details or reset their password by email.

Refer to [LLDAP's configuration file](https://github.com/lldap/lldap/blob/main/lldap_config.docker_template.toml);
config variables are prefixed with `LLDAP_` or `LLDAP_<SECTION>_` when passed as env vars.

## Configuration Notes

- [LLDAP — Declarative Selfhosted Lightweight Authentication · Stonegarden](https://blog.stonegarden.dev/articles/2025/01/lldap/)
- [Custom OIDC claims with Argo CD and Audiobookshelf · Stonegarden](https://blog.stonegarden.dev/articles/2025/07/custom-oidc-claims/)

### Grafana

1. Add `grafana:admin` and `grafana:viewer` groups
2. Add appropriate users to each group

## View LLDAP Objects

Prerequisites: `openldap` (brew), `ldap-utils` (apt), or `openldap-clients` (dnf, yum, apk)

After port-forwarding the LLDAP container:

```sh
kubectl port-forward service/lldap 3890:3890 -n security
```

```sh
USER="admin"
DC1="home"
DC2="arpa"
ldapsearch -H ldap://localhost:3890 \
  -D "uid=${USER},ou=people,dc=${DC1},dc=${DC2}" -W \
  -b "dc=${DC1},dc=${DC2}" "(objectClass=*)"
```

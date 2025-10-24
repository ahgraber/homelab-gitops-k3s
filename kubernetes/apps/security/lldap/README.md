# [lldap](https://github.com/lldap/lldap)

A lightweight authentication server that provides an opinionated, simplified LDAP interface for authentication. It comes with a frontend that makes user management easy, and allows users to edit their own details or reset their password by email.

The goal is not to provide a full LDAP server, but to integrate with many backend that support LDAP as a source of external authentication.

Refer to [LLDAP's configuration file](https://github.com/lldap/lldap/blob/main/lldap_config.docker_template.toml);
config variables are prefixed with `LLDAP_` or `LLDAP_<SECTION>_` when passed as env vars.

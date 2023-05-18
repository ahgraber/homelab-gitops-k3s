# Postgresql

This stack deploys an 'operated', centralized postgresql cluster via cloudnative-pg's operator.
Movetokube's ext-postgres-operator is deployed to automate provisioning per-app users and databases.
pgadmin is deployed for webUI-based db administration and querying.

Alternatively, an [`initdb`](https://github.com/onedr0p/containers/tree/main/apps/postgres-initdb) can be [attached
to deployments as an initContainer](https://github.com/onedr0p/home-ops/blob/74133ad006a1fed52a87b8163d3f7b9a2e22e75b/kubernetes/archive/default/guacamole/app/guacamole/helmrelease.yaml)
and used to provision application databases.

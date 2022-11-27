# Databases

## Modularity

For ease of experimentation, use a modular approach --
deploy a single instance of each db application (mariadb/postgres/redis/etc.)
per application as required.

This assumes that HA is not required (multiple HA deployements become resource-hogs),
and that downtime is OK, assuming good backup policy.

For applications that make it to 'production', consider HA database deployments,
or migrate to a cluster-wide HA db application.

## HA

The alternative is to deploy cluster-wide HA db applications with per-app internal databases.
However, this is potentially more fragile in light of the experimentation seen in this homelab cluster.

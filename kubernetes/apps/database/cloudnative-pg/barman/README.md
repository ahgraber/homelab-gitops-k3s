# CNPG Barman Cloud Plugin

Installs CloudNativePG's Barman Cloud plugin (CNPG-I) via the upstream Helm chart.

This enables the `ObjectStore` CRD (`barmancloud.cnpg.io/v1`) and the plugin service `barman-cloud.cloudnative-pg.io` used by CNPG `Cluster.spec.plugins` and plugin-based `Backup`/`ScheduledBackup`.

## Notes

- This chart creates cert-manager resources (`Issuer`/`Certificate`). Ensure cert-manager is installed first.
- The plugin is installed into the `database` namespace to match the CNPG operator in this repo.

## Upgrading

Bump `.spec.ref.tag` in [plugin-barman-cloud-source.yaml](plugin-barman-cloud-source.yaml) (chart version).

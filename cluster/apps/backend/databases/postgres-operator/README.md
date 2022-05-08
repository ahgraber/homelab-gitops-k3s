# Zalando postgres operator

[Zalando operator](https://github.com/zalando/postgres-operator) creates highly available databases

The [Operator](operator.yaml) and [Operator UI](operator-ui.yaml) will watch the specified namespaces in the
_kubernetes cluster_ for additions/revisions to _postgres cluster_ manifests,
which define databases and associated users, permissions, configuration, etc.

## References

- [operator administration/configuration](https://github.com/zalando/postgres-operator/blob/master/docs/administrator.md)
- [cluster manifest](https://github.com/zalando/postgres-operator/blob/master/docs/reference/cluster_manifest.md)
- [spilo image variables](https://github.com/zalando/spilo/blob/master/ENVIRONMENT.rst)

## Snippets & Troubleshooting

- patroni manages the cluster
  - `patronictl list` - list member and status
  - `patronictl reinit <cluster> <member>` - reinit broken node

- get status of all clusters

  ```sh
  kubectl get pods -A -o name | grep postgres-0 | xargs -I{} kubectl exec {} -- patronictl list
  ```

- delete clsuter

  ```sh
  kubectl delete postgres <cluster-name> -n <namespace>
  ```

- cannot re-create DB cluster:

  ```sh
  kubectl delete poddisruptionbudgets postgres-<chart name>-zalando-postgres-cluster-postgres-pdb
  ```

- apply backup:
  1. get into LEADER postgres node
  2. delete old DB:

     ```sh
     psql -U postgres -c 'drop database "tt-rss"'
     ```

  3. `apt update && apt install -y openssh-client`
  4. `rsync anunez@nas:/volume1/kubernetes/backup/db/tt-rss/backup .`
  5. `psql -U postgres -f backup`

- reinit member of cluster:

  ```sh
  kubectl exec -ti recipes-db-zalando-postgres-cluster-postgres-2 -- patronictl reinit <cluster name> <cluster member>
  ```

## Major version upgrades

In-place major version upgrades can be configured to be executed by the operator with the `major_version_upgrade_mode` option.

By default it is set to `off` which means the cluster version will not change when increased in the manifest.
In this scenario the major version could be run by a user from within the master pod. Exec into the container and run:

```sh
# N is number of members in given postgres cluster
su postgres -c "python3 /scripts/inplace_upgrade.py <N>"
```

When major_version_upgrade_mode is set to `manual` the operator will run the upgrade script automatically
after the _postgres cluster_ manifest is updated and pods are rotated.

[ref](https://github.com/zalando/spilo/pull/488)

- in-place upgrade:

# [Just](https://github.com/casey/just)

`just` is the command runner used by this repository.

## Use

List all available recipes (grouped by domain):

```sh
just --list
```

List recipes in a module:

```sh
just --list <module>
```

Available modules: `ansible`, `kube`, `rook`, `mlflow`

Root-level recipes are grouped under `repository` and `sops`.

Run a recipe:

```sh
just <module> <recipe>
```

Pass positional arguments:

```sh
just <module> <recipe> <arg1> <arg2>
```

Pass extra CLI flags after `--` when a recipe supports variadic args:

```sh
just <module> <recipe> <required-arg> -- --flag --another-flag
```

## Module Layout

Modules are colocated with the directories they manage:

| Module    | File                                 | Domain                            |
| --------- | ------------------------------------ | --------------------------------- |
| `ansible` | `ansible/mod.just`                   | Ansible operations                |
| `kube`    | `kubernetes/mod.just`                | Cluster, Flux, DB, VolSync, Debug |
| `rook`    | `kubernetes/apps/rook-ceph/mod.just` | Rook-Ceph operations              |
| `mlflow`  | `.just/mlflow/mod.just`              | MLflow trace management           |

The `kube` module uses groups to organize recipes.
Run `just --list kube` to see recipes organized by: cluster, flux, db, volsync, debug.

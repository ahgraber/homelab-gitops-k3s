# Crunchydata postgres operator

[Crunchydata postgres operator](https://github.com/CrunchyData/postgres-operator) creates highly available databases

The Operator will watch the specified namespace(s) in the
_kubernetes cluster_ for additions/revisions to _postgres cluster_ manifests,
which define databases and associated users, permissions, configuration, etc.

Crunchydata provides examples to deploy either as kustomize/manifests or via helm

## [User Mgmt](https://access.crunchydata.com/documentation/postgres-operator/v5/architecture/user-management/)

When you create a Postgres cluster with PGO and do not specify any additional users or databases, PGO will do the following:

- Create a database that matches the name of the Postgres cluster.
- Create an unprivileged Postgres user with the name of the cluster.
  This user has access to the database created in the previous step.
- Create a Secret with the login credentials and connection details for the Postgres user in relation to the database.
  This is stored in a Secret named `<clusterName>-pguser-<clusterName>`. These credentials include:
  - `user`: The name of the user account.
  - `password`: The password for the user account.
  - `dbname`: The name of the database that the user has access to by default.
  - `host`: The name of the host of the database. This references the Service of the primary Postgres instance.
  - `port`: The port that the database is listening on.
  - `uri`: A PostgreSQL connection URI that provides all the information for logging into the Postgres database.
  - `jdbc-uri`: A PostgreSQL JDBC connection URI that provides all the information for logging into the Postgres database via the JDBC driver.

## References

- [examples](https://github.com/CrunchyData/postgres-operator-examples)

## Monitoring

- [examples](https://github.com/CrunchyData/postgres-operator-examples/tree/main/kustomize/monitoring)

# pgadmin

Administrative/interactive interface for postgres databases

## Connecting to databases

Postgres database connection strings take the format
`postgresql://user:password@host[:port]/database_name`,
where `POSTGRES_HOST` on k8s has a FQDN like `service.namespace.svc.cluster.local`

# ext-postgres-operator

Operator that watches CRs for instructions to create db and user(s).
Manages auth and db urlstrings as kubernetes secrets.

## example CR

```yaml
---
apiVersion: db.movetokube.com/v1alpha1
kind: Postgres
metadata:
  name: &app <app>
  namespace: &namespace default
  annotations:
    postgres.db.movetokube.com/instance: *namespace
spec:
  database: *app # db name in postgres cluster
---
apiVersion: db.movetokube.com/v1alpha1
kind: PostgresUser
metadata:
  name: &app <app>-user
  namespace: &namespace default
  annotations:
    postgres.db.movetokube.com/instance: *namespace
spec:
  role: *app
  database: *app # references the CR
  secretName: database
  privileges: OWNER
```

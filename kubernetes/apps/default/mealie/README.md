# [Mealie](https://hay-kot.github.io/mealie/)

A self-hosted recipe manager and meal planner with a RestAPI backend and a r
eactive frontend application built in Vue for a pleasant user experience for the whole family.

## Long-running queries

To find long-running queries, run:

```sql
SELECT
  pid,
  now() - pg_stat_activity.query_start AS duration,
  query,
  state
FROM pg_stat_activity
WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes';
```

To (safely) cancel query:

```sql
SELECT pg_cancel_backend(<pid>);
```

To force-terminate:

```sql
SELECT pg_terminate_backend(<pid>);
```

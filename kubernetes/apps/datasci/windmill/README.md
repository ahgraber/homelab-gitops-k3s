# [Windmill](https://www.windmill.dev/docs)

Windmill is an open-source, blazing fast and scalable alternative to Retool, Airplane, Superblocks, n8n, Airflow, Temporal
to build all your internal tools (endpoints, workflows, UIs)
through the combination of code (in Typescript, Python, Go, Bash, SQL or any docker image)
and low code builders.

It embeds all-in-one:

- an execution runtime to execute functions at scale with low-latency and no overhead on a fleet of workers
- an orchestrator to compose functions into powerful flows at low-latency built with a low-code builder (or yaml if that's your thing)
- an app builder to build application and data-intensive dashboards built with low-code or JS frameworks such a React.

Windmill can be used solely from its UI through its webIDE, and low-code builders
but it is also possible to keep using your editor and deploy from a git repo using a CLI.

## GitOps

Github Actions can be used to sync code <--> Windmill.  See [examples](https://github.com/windmill-labs/windmill-sync-example/tree/main)

## Database

See [note](https://www.windmill.dev/docs/advanced/self_host#run-windmill-without-using-a-postgres-superuser) about using a 'nonstandard' username.
Windmill expects `windmill_user` and `windmill_admin` roles:

```sql
-- NOTE: MAKE SURE DATABASE CONNECTION IS CORRECT
-- Database: windmill
CREATE ROLE windmill_user;

GRANT ALL
ON ALL TABLES IN SCHEMA public
TO windmill_user;

GRANT ALL PRIVILEGES
ON ALL SEQUENCES IN SCHEMA public
TO windmill_user;

ALTER DEFAULT PRIVILEGES
    IN SCHEMA public
    GRANT ALL ON TABLES TO windmill_user;

ALTER DEFAULT PRIVILEGES
    IN SCHEMA public
    GRANT ALL ON SEQUENCES TO windmill_user;


CREATE ROLE windmill_admin WITH BYPASSRLS;
GRANT windmill_user TO windmill_admin;
GRANT windmill_user TO "windmill-<HASH>";
GRANT windmill_admin TO "windmill-<HASH>";
```

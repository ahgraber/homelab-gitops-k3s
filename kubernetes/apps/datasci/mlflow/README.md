# [MLFlow](https://mlflow.org/docs/latest/index.html)

MLflow is a platform to streamline machine learning development, including tracking experiments, packaging code into reproducible runs, and sharing and deploying models.

## First Start

`InitContainer` is not needed on first start; it will cause the deployment to fail because it cannot find tables to update!

## Tracking Server

[MLflow](https://mlflow.org) provides for diverse [tracking server configurations](https://mlflow.org/docs/latest/tracking.html#common-setups); among them are:

- MLflow as remote Tracking Server, providing tracking backend and proxied access to artifact stores
- MLflow as Artifact Server only, providing proxied access to artifacts but no tracking
- MLflow Tracking Server only, and requiring direct access to the artifact store.
  In this configuration, the user must manage their direct connection to the artifact store

MLflow uses two components for storage: backend store and artifact store.
The **backend store** persists MLflow entities (_runs_, parameters, metrics, tags, notes, metadata, etc), and these data can be recorded to local files, to a SQLAlchemy compatible database, or remotely to a tracking server.
The **artifact store** persists _artifacts_ (files, models, images, in-memory objects, or model summary, etc) to local files or a variety of remote file storage solutions.

> IMPORTANT
> See notes in MLFlow docs regarding the differences between options 4 and 5
> with respect to user authorization / access permissions

### Cleaning up deleted experiments

The `gc` CronJob runs `mlflow gc --older-than=30d` every Sunday at 03:00 America/New_York.
It permanently removes runs, experiments, and logged models that have been in the `deleted` lifecycle stage for at least 30 days, along with their artifacts.
Because artifacts are proxied by the tracking server (`--serve-artifacts`), the job sets `MLFLOW_TRACKING_URI` to the in-cluster service so `gc` can resolve `mlflow-artifacts:` URIs; `mlflow.datasci.svc.cluster.local:*` must therefore stay in `MLFLOW_SERVER_ALLOWED_HOSTS`.

> The gc bug below still affects this job.
> Check failed jobs with `kubectl logs -n datasci job/<job-name>`.

Manual cleanup:

- Run `mlflow gc` in the mlflow container to clean up deleted runs and artifacts (this retains the experiment).
  The python script `cleanup-runs.py` may also be used to clean up runs from the database (this may orphan the artifacts).
  See more: [[BUG] gc fails with postgres backend, violates foreign key constraint · Issue #13254 · mlflow/mlflow](https://github.com/mlflow/mlflow/issues/13254)
- Run the python script `cleanup-experiments.py` to fully delete experiments from the database

### Deleting traces

The repo includes a `just` module for MLflow trace deletion using `MlflowClient.delete_traces()`:

```sh
# delete traces older than 7 days
just mlflow delete-traces-older 1 7

# delete explicit trace IDs (comma-separated)
just mlflow delete-traces-ids 1 trace_id_1,trace_id_2

# delete trace IDs from a file (one ID per line)
just mlflow delete-traces-file 1 ./trace_ids.txt
```

Use `tracking_uri` when deleting against a non-default endpoint:

```sh
just mlflow delete-traces-older 1 7 https://mlflow.example.com
```

## Metrics

The server runs with `--expose-prometheus=/tmp/metrics`, which activates the `prometheus-flask-exporter` and serves request metrics (prefixed `mlflow_`) at `/metrics`.
A `ServiceMonitor` scrapes that endpoint every minute; kube-prometheus-stack discovers ServiceMonitors in all namespaces, so no extra label is needed.

The `/metrics` endpoint is served on the same port as the UI and is not protected by authentication.

## AI Gateway

As of MLflow v3.9, the [MLflow AI Gateway](https://mlflow.org/docs/latest/genai/governance/ai-gateway/) is now a part of the tracking server and does not require independent deployment.

The standalone Gateway Server mode (`mlflow gateway start --config-path ...`) is still available as a legacy path, but is not used in this deployment.

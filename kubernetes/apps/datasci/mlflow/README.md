# [MLFlow](https://mlflow.org/docs/latest/index.html)

MLflow is a platform to streamline machine learning development,
including tracking experiments, packaging code into reproducible runs, and sharing and deploying models.

## First Start

`InitContainer` is not needed on first start; it will cause the deployment to fail because it cannot find tables to update!

## Tracking Server

[MLflow](https://mlflow.org) provides for diverse [tracking server configurations](https://mlflow.org/docs/latest/tracking.html#common-setups);
among them are:

- MLflow as remote Tracking Server, providing tracking backend and proxied access to artifact stores
- MLflow as Artifact Server only, providing proxied access to artifacts but no tracking
- MLflow Tracking Server only, and requiring direct access to the artifact store.
  In this configuration, the user must manage their direct connection to the artifact store

MLflow uses two components for storage: backend store and artifact store.
The **backend store** persists MLflow entities (_runs_, parameters, metrics, tags, notes, metadata, etc), and
these data can be recorded to local files, to a SQLAlchemy compatible database, or remotely to a tracking server
The **artifact store** persists _artifacts_ (files, models, images, in-memory objects, or model summary, etc)
to local files or a variety of remote file storage solutions.

> IMPORTANT
> See notes in MLFlow docs regarding the differences between options 4 and 5
> with respect to user authorization / access permissions

### Cleaning up deleted experiments

- Run `mlflow gc` in the mlflow container to clean up deleted runs and artifacts (this retains the experiment).
  The python script `cleanup-runs.py` may also be used to clean up runs from the database (this may orphan the artifacts).
  See more: [[BUG] gc fails with postgres backend, violates foreign key constraint · Issue #13254 · mlflow/mlflow](https://github.com/mlflow/mlflow/issues/13254)
- Run the python script `cleanup-experiments.py` to fully delete experiments from the database

## Gateway Server

This container can also be used to deploy the [MLflow AI Gateway](https://mlflow.org/docs/latest/llms/deployments/index.html)
Follow the instructions in the MLflow documentation to create a `config.yaml` file
with the specifications for the AI API services that will be routed through the AI Gateway.

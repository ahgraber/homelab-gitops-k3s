# [MLFlow](https://mlflow.org/docs/latest/index.html)

MLflow is a platform to streamline machine learning development,
including tracking experiments, packaging code into reproducible runs, and sharing and deploying models.

## Use

MLflow posits 6 scenarios for use, but only the latter 3 apply to a k8s deployment:

1. ~MLflow on localhost~
2. ~MLflow on localhost with SQLite~
3. ~MLflow on localhost with Tracking Server~
4. MLflow with remote Tracking Server, backend and artifact stores
5. MLflow Tracking Server enabled with proxied artifact storage access
6. MLflow Tracking Server used exclusively as proxied access host for artifact storage access

MLflow uses two components for storage: backend store and artifact store.
The backend store persists MLflow entities (runs, parameters, metrics, tags, notes, metadata, etc),
and these data can be recorded to local files, to a SQLAlchemy compatible database, or remotely to a tracking server

The artifact store persists artifacts (files, models, images, in-memory objects, or model summary, etc)
to local files or a variety of remote file storage solutions.

> IMPORTANT
> See notes in MLFlow docs regarding the differences between options 4 and 5
> with respect to user authorization / access permissions

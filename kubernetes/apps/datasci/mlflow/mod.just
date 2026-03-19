set quiet := true
set shell := ["bash", "-euo", "pipefail", "-c"]

mlflow_scripts := source_directory() + "/scripts"

[private]
default:
    just --list mlflow

[doc("Delete traces older than N days")]
delete-traces-older experiment_id days tracking_uri="":
    uv run --with mlflow '{{ mlflow_scripts }}/delete_traces.py' older-than-days --experiment-id {{ experiment_id }} --days {{ days }} {{ if tracking_uri != "" { "--tracking-uri " + tracking_uri } else { "" } }}

[doc("Delete specific traces by comma-separated IDs")]
delete-traces-ids experiment_id trace_ids tracking_uri="":
    uv run --with mlflow '{{ mlflow_scripts }}/delete_traces.py' trace-ids --experiment-id {{ experiment_id }} --trace-ids {{ trace_ids }} {{ if tracking_uri != "" { "--tracking-uri " + tracking_uri } else { "" } }}

[doc("Delete trace IDs from a file (one trace ID per line)")]
delete-traces-file experiment_id file tracking_uri="":
    uv run --with mlflow '{{ mlflow_scripts }}/delete_traces.py' trace-ids --experiment-id {{ experiment_id }} --trace-ids-file {{ file }} {{ if tracking_uri != "" { "--tracking-uri " + tracking_uri } else { "" } }}

# [Loki](https://grafana.com/oss/loki/)

> Like Prometheus, but for logs!

Loki is a _log_ aggregation system designed to store and query logs from all your applications and infrastructure.
From the makers of Grafana.

Grafana Loki is a set of components that can be composed into a fully featured logging stack.

Unlike other logging systems, Loki is built around the idea of only indexing metadata about your logs -- labels
Log data itself is then compressed and stored in chunks in object stores such as S3 or GCS,
or even locally on the filesystem. A small index and highly compressed chunks simplifies the operation and
significantly lowers the cost of Loki.

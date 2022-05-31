# Promtail

Promtail is an agent which ships the contents of local logs to a private Grafana Loki instance or Grafana Cloud.
It is usually deployed to every machine that has applications needed to be monitored.

It primarily:

- Discovers targets
- Attaches labels to log streams
- Pushes them to the Loki instance.

-
Currently, Promtail can tail logs from two sources: local log files and the systemd journal (on AMD64 machines only).

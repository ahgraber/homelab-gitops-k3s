# Databases

Current approach is a single HA deployment of each db application (postgres, redis),
with per-app databases internally.

It is also possible to do per-app deployments of database instances,
but if HA is required it might get resource-intensive

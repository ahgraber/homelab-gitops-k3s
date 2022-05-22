# [Thanos](https://thanos.io/)

Open source, highly available Prometheus setup with long term storage capabilities

Thanos is made of a set of components with each filling a specific role.

- Sidecar: connects to Prometheus, reads its data for query and/or uploads it to cloud storage.
- Store Gateway: serves metrics inside of a cloud storage bucket.
- Compactor: compacts, downsamples and applies retention on the data stored in cloud storage bucket.
- Receiver: receives data from Prometheus's remote-write WAL, exposes it and/or upload it to cloud storage.
- Ruler/Rule: evaluates recording and alerting rules against data in Thanos for exposition and/or upload.
- Querier/Query: implements Prometheus's v1 API to aggregate data from the underlying components.
- Query Frontend: implements Prometheus's v1 API proxies it to Query while caching the response
  and optional splitting by queries day.

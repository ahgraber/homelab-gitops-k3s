# External Services

This leverages kubernetes networking resources (Service, Endpoint, Ingress) to allow k8s-gateway and nginx to act as reverse proxy for services not hosted within the k8s cluster.

See also [proxy to external services](https://kristhecodingunicorn.com/post/k8s_proxy_svc/#proxy-to-external-services-with-service-without-selectors)

## Gotchas

### `garage-s3`: compression must stay off

The gateway-wide `envoy` BackendTrafficPolicy enables Brotli/Gzip compression on every route.
Envoy Gateway implements that by adding `accept-encoding` to the route's `request_headers_to_remove`, so the origin never sees the header.

AWS SigV4 clients built on `aws-sdk-go-v2` (Litestream >= 0.5.7, for example) send `Accept-Encoding: identity` and list `accept-encoding` in `SignedHeaders`.
Garage recomputes the signature, cannot find the header, and returns `403 ... header not present`.
Clients that do not sign the header (boto3, restic's minio-go) are unaffected, which is why most S3 traffic through this route works.

`garage-s3.yaml` therefore carries its own route-scoped BackendTrafficPolicy with no `compression` block.
It sets no `mergeType`, so it replaces the gateway-wide policy for this route rather than merging with it - keep the other settings in the two policies in sync.

Litestream's own workaround ([#1394](https://github.com/benbjohnson/litestream/pull/1394)) excludes `Accept-Encoding` from signing only for `googleapis.com` hosts, so it does not help here.

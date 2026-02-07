# [Envoy Gateway](https://github.com/envoyproxy/gateway)

Manages Envoy Proxy as a Standalone or Kubernetes-based Application Gateway

## Network Security

`envoy-external` is intended to be reachable only through the Cloudflare tunnel.
A NetworkPolicy restricts ingress to the `envoy-external` data plane so only `cloudflared` pods can connect on ports 80/443 (plus Prometheus scraping on the metrics port).

If the Envoy Gateway pod labels change, update the NetworkPolicy selector in:

- `kubernetes/apps/network/envoy-gateway/instance/networkpolicy-external.yaml`

## References

- [Test with SSLLabs](https://www.ssllabs.com/ssltest/)

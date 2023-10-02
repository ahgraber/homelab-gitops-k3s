# [k8s-gateway](https://github.com/ori-edge/k8s_gateway)

A CoreDNS plugin to resolve all types of external Kubernetes resources.

`k8s_gateway` will provide DNS resolution to Kubernetes entrypoints from any device that uses your home DNS server.
For this to work, your home DNS server must be configured to forward DNS queries for `${bootstrap_cloudflare_domain}`
to `${bootstrap_k8s_gateway_addr}` instead of the upstream DNS server(s) it normally uses.
This is a form of **split DNS** (aka split-horizon DNS / conditional forwarding).

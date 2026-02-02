# 🌐 Networking

```txt
           "appname.domain.com"

       internal:             external:

                         ┌───────────────┐
      *dns lookup*       │ external-dns  │
           │             │   creates     │
           ▼             │  dns record   │
       split-dns:        └──────┬────────┘
     if domain.com:             │
    use k8s_gateway             ▼
      as resolver          *dns lookup*
           │                    │
           │                    │
   ┌───────▼───────┐            ▼
   │  k8s_gateway  │          public
   │  10.2.118.2   │       cloudflare IP
   └───────┬─┬─────┘            │
           │ │                  │
           │ │                ┌─▼─────────────┐
           │ │                │               │
┌──────────┼─┼────────────────┤  cloudflared  │
│          │ │                │               │
│          │ └────────┐       └──┬──────────┬─┘
│          │          │          │          │
│  ┌───────▼───────┐  │  ┌───────▼───────┐  │
│  │   internal    │  │  │   external    │  │
│  │ envoy-gateway │  └──► envoy-gateway │  │
│  │  10.2.118.5   │     │  10.2.118.4   │  │
│  └───────┬───────┘     └───────┬───────┘  │
│          │                     │          │
│          │                     │          │
│  ┌───────▼───────┐     ┌───────▼───────┐  │
│  │   internal    │     │   external    │  │
│  │  application  │     │  application  │  │
│  └───────────────┘     └───────────────┘  │
│                                           │
└───────────────────────────────────────────┘
 k8s cluster
 https://asciiflow.com/
```

## 🌎 Public Applications

The `external-dns` application will create public DNS records.
External-facing application access relies on a `cloudflared` tunnel to access the external `envoy-gateway`, which acts as a reverse proxy to the application.

Any HTTPRoute attached to the `envoy-external` gateway is reachable from the public internet.
To make applications public, set the correct gateway name and annotations (see the `echo-server` HelmRelease for an example).

## 🏠 Private Applications

`k8s_gateway` provides DNS resolution to Kubernetes entrypoints from any device using the LAN (home network) DNS server.
For this to work, the DNS server must be configured to forward DNS queries for `${bootstrap_cloudflare_domain}` to `${bootstrap_k8s_gateway_addr}` instead of the upstream DNS server(s) it normally uses.
This is a form of **split DNS** (aka split-horizon DNS / conditional forwarding).

Internal/Private applications will access external and/or internal envoy gateway local/private IP(s) provided by k8s_gateway

## 🔐 Network Security

Public access is intended to flow only through the Cloudflare Tunnel into the `envoy-external` gateway.

Risks that may bypass this design:

- ISP or homelab router port forwards/DMZ rules to `10.2.118.4` (envoy-external),
  `10.2.118.5` (envoy-internal), or any node IPs.
- UPnP/NAT-PMP automatically opening inbound ports.
- Public IPv6 exposure on nodes or routers.

In-cluster mitigation:

- A NetworkPolicy restricts access to `envoy-external` so only `cloudflared` pods and RFC1918 sources can reach it.
  This allows internal LAN access to `envoy-external` while still blocking non-private internet sources.

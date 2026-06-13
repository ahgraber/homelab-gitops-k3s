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
   │   <gw-vip>    │       cloudflare IP
   └───────┬───────┘            │
           │                    │
           │                  ┌─▼─────────────┐
           │                  │               │
┌──────────┼──────────────────┤  cloudflared  │
│          │                  │               │
│          │                  └──┬──────────┬─┘
│          │                     │          │
│  ┌───────▼───────┐     ┌───────▼───────┐  │
│  │   internal    │     │   external    │  │
│  │ envoy-gateway │     │ envoy-gateway │  │
│  │  <int-vip>    │     │  <ext-vip>    │  │
│  └───────┬─┬─────┘     └───────┬───────┘  │
│          │ └─────────────────┐ │          │
│          │                   │ │          │
│  ┌───────▼───────┐     ┌─────▼─▼───────┐  │
│  │   internal    │     │   external    │  │
│  │  application  │     │  application  │  │
│  └───────────────┘     └───────────────┘  │
│                                           │
└───────────────────────────────────────────┘
 k8s cluster
 https://asciiflow.com/
```

## 🏠 Private Applications

`k8s_gateway` provides DNS resolution to Kubernetes entrypoints from any device using the LAN (home network) DNS server.
For this to work, the DNS server must be configured to forward DNS queries for `${bootstrap_cloudflare_domain}` to `${bootstrap_k8s_gateway_addr}` instead of the upstream DNS server(s) it normally uses.
This is a form of **split DNS** (aka split-horizon DNS / conditional forwarding).

`k8s_gateway` returns the internal Envoy Gateway VIP so internal clients always reach `envoy-internal`.
Any app that should be reachable on the LAN must attach its HTTPRoute to `envoy-internal`.

## 🌎 Public Applications

The `external-dns` application will create public DNS records.
External-facing application access relies on a `cloudflared` tunnel to access the external `envoy-gateway`, which acts as a reverse proxy to the application.

Any HTTPRoute attached to the `envoy-external` gateway is reachable from the public internet.

## 🔐 Network Security

Public access is intended to flow only through the Cloudflare Tunnel into the `envoy-external` gateway.

Risks that may bypass this design:

- ISP or homelab router port forwards/DMZ rules to `<ext-vip>` (envoy-external),
  `<int-vip>` (envoy-internal), or any node IPs.
- UPnP/NAT-PMP automatically opening inbound ports.
- Public IPv6 exposure on nodes or routers.

In-cluster mitigation:

- A NetworkPolicy restricts access to `envoy-external` so only `cloudflared` pods can reach it.
  Internal LAN and in-cluster access should use `envoy-internal` instead.

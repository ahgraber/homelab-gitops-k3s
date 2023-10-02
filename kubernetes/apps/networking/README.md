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
│  │ ingress-nginx │  └──► ingress-nginx │  │
│  │  10.2.118.3   │     │  10.2.118.4   │  │
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
External-facing application access relies on a `cloudflared` tunnel to access the external `ingress-nginx`,
which acts as a reverse proxy to the application.

By default, `echo-server` and the `flux-webhook` are the only subdomains reachable from the public internet.
In order to make additional applications public you must set set the correct ingress class name and ingress annotations (see the `echo-server` HelmRelease).

## 🏠 Private Applications

`k8s_gateway` will provide DNS resolution to Kubernetes entrypoints from any device that uses your home DNS server.
For this to work, your home DNS server must be configured to forward DNS queries for `${bootstrap_cloudflare_domain}` to `${bootstrap_k8s_gateway_addr}` instead of the upstream DNS server(s) it normally uses.
This is a form of **split DNS** (aka split-horizon DNS / conditional forwarding).

Internal/Private applications will access external and/or internal ingress-nginx local/private IP(s) provided by k8s_gateway

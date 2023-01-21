# Traefik Middlewares

- [Traefik Middlewares](#traefik-middlewares)

> Middlewares are applied in the same order as their declaration in router
>

## _defaults

Creates a `default` middleware by:

1. Forcing http --> https
2. Setting standardized headers
3. Sets X-Real-Ip correctly from Cloudflare tunnel
4. Adds redirects to error pages

## basicauth

Requires a simple password login

## error-pages

Redirects errors to `error-pages` deployment

## headers-default

Sets standard headers

## ips-cloudflare

ipAllowList for Cloudflare IPs ([IPv4]( https://www.cloudflare.com/ips-v4) and [IPv6](https://www.cloudflare.com/ips-v6))

> Currently not used, since using Cloudflare Tunnels with `cloudflared` doesn't seem to pass
> cloudflare IPs in X-Forwarded-For

## ips-github-hooks

IP addresses used for github hooks

## ips-rfc1918

IP addresses from private rfc1918 standard

## plugins

### plugin-cf-realip-xff

Uses [Paxxs/traefik-get-real-ip](github.com/Paxxs/traefik-get-real-ip) to identify actual source IP
when passed from cloudflare tunnel.
Requires setting a transform rule in cloudflare dashboard > rules > transform-rules > modify-request-header
to create unique header name:value so plugin knows when to act.

## redirects

Creates standard redirects (http --> https, regex, etc.)

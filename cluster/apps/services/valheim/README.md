# Valheim

Creates a local Valheim server based on [lloesche/valheim-server-docker](https://github.com/lloesche/valheim-server-docker).

## Networking

Relies on `metallb` to expose a separate external IP.  This means that Ingress will not handle the traffic.
To get to `supervisor`, go to `http://valheim.<domain>.com:9001`

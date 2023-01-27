# [Whoami](https://github.com/traefik/whoami)

Tiny Go webserver that prints os information and HTTP request to output

## References

* [traefik & whoami quickstart](https://doc.traefik.io/traefik/getting-started/quick-start/)

## Examples

### Internal

```ini
# internal
Hostname: whoami-8588f96d46-dwvf8
IP: 127.0.0.1
IP: ::1
IP: 10.42.229.215  # traefik
IP: fe80::44e3:4ff:fe93:6d38
RemoteAddr: 10.42.229.216:53894
# ...
Upgrade-Insecure-Requests: 1
X-Forwarded-For: <internal ip>  # my ip
X-Forwarded-Host: whoami.ninerealmlabs.com
X-Forwarded-Port: 443
X-Forwarded-Proto: https
X-Forwarded-Server: traefik-ctf9x
X-Real-Ip: <internal ip>  # my ip
```

### External

```ini
# external
Hostname: whoami-8588f96d46-dwvf8
IP: 127.0.0.1
IP: ::1
IP: 10.42.229.215  # traefik
IP: fe80::44e3:4ff:fe93:6d38
RemoteAddr: 10.42.47.219:56412
# ...
Cdn-Loop: cloudflare
Cf-Connecting-Ip: 52.152.200.185  # my ip
# ...
Upgrade-Insecure-Requests: 1
X-Forwarded-For: <external ip>, 10.42.210.127  # real-ip, cloudflared pod
X-Forwarded-Host: whoami.ninerealmlabs.com
X-Forwarded-Port: 443
X-Forwarded-Proto: https
X-Forwarded-Server: traefik-5kdgs
X-Real-Ip: <external ip>  # with traefik-get-real-ip plugin
```

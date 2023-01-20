# [Crowdsec](https://crowdsec.net)

CrowdSec offers a crowd-based cybersecurity suite to protect your online services,
visualize & act upon threats, and a TIP (Threat Intel Platform) to block malicious IPs.

## K8s vs metal install

Crowdsec is installed on the nodes using ansible (see [homelab-infra](https://github.com/ahgraber/homelab-infra)).
The node installation watches LAN traffic and protects the nodes themselves.
The k8s installation watches ingress and protects the cluster.

## Secrets

1. Crowsec secret must be (manually) created from the centralized [web portal](https://app.crowdsec.net/instances).

## References

- [1. crowdsec with k8s - integration](https://crowdsec.net/blog/kubernetes-crowdsec-integration/)
- [2. crowdsec with k8s - remediation](https://crowdsec.net/blog/kubernetes-crowdsec-integration-remediation/)
- [3. how to mitigate security threats with crowdsec and traefik](https://www.crowdsec.net/blog/how-to-mitigate-security-threats-with-crowdsec-and-traefik)

## [Traefik Crowdsec Bouncer](https://github.com/fbonalair/traefik-crowdsec-bouncer)

A http service to verify request and bounce them according to decisions made by CrowdSec.

### Secrets

Crowdsec bouncer API key must be (manually) generated from crowdsec LAPI.

```sh
# in crowdsec pod cli
cscli bouncers add traefik-ingress
```

### Integration with traefik

Traefik middleware is created automatically by deployment, and can be used by ingresses and ingressroutes,
or applied to all traffic on specific endpoints

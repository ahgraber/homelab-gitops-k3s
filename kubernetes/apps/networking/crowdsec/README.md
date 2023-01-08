# [Crowdsec](https://crowdsec.net)

CrowdSec offers a crowd-based cybersecurity suite to protect your online services, visualize & act upon threats, and a TIP (Threat Intel Platform) to block malicious IPs.

## Secrets

1. Crowsec secret must be (manually) created from the centralized [web portal](https://app.crowdsec.net/instances).
2. Crowdsec bouncer API key must be (manually) generated from crowdsec agent.

   ```sh
   # in crowdsec pod cli
   cscli bouncers add k8s-traefik
   ```

References:

- [crowdsec with k8s - integration](https://crowdsec.net/blog/kubernetes-crowdsec-integration/)
- [how to mitigate security threats with crowdsec and traefik](https://www.crowdsec.net/blog/how-to-mitigate-security-threats-with-crowdsec-and-traefik)
- [crowdsec with k8s - remediation](https://crowdsec.net/blog/kubernetes-crowdsec-integration-remediation/)

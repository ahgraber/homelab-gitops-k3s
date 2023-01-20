# [Traefik Ingress](https://doc.traefik.io/traefik/providers/kubernetes-ingress/)

The Traefik Kubernetes Ingress provider is a Kubernetes Ingress controller;
that is to say, it manages access to cluster services by supporting the Ingress specification.

## References

* [tls configuration](https://en.tferdinand.net/traefik-2-tls-configuration//)
* [Test with SSLLabs](https://www.ssllabs.com/ssltest/)

## Plugins

The following plugins may be useful to edit headers/values

```yaml
  values:
    # ...
    additionalArguments:
      # rewrite headers/values
      - "--experimental.plugins.htransformation.modulename=github.com/tomMoulard/htransformation"
      - "--experimental.plugins.htransformation.version=v0.2.7"
      # updated/more configurable header transform
      - "--experimental.plugins.htransformation.modulename=github.com/adyanth/header-transform"
      - "--experimental.plugins.htransformation.version=v1.0.0"
```

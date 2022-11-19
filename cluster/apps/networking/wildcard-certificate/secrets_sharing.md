# Share secrets across namespaces

Cluster can use `reflector` to copy secrets across namespaces. In particular, this can share the tls
certificates from `networking` to `security`.

- Cert-manager's [faq](https://cert-manager.io/docs/faq/kubed/)
- [Emberstack Reflector](https://github.com/emberstack/kubernetes-reflector)

## Process

1. `reflector` will check secrets for an annotation indicating it may be replicated to other namespaces

   ```yaml
   apiVersion: v1
   kind: Secret
   metadata:
     name: <SECRET_NAME>
     namespace: <SECRET_NAMESPACE>
     annotations:
       reflector.v1.k8s.emberstack.com/reflection-allowed: "true"
       reflector.v1.k8s.emberstack.com/reflection-allowed-namespaces: "ns1,ns2,..." # "" (empty) == all namespaces
       # automatically create mirrored resources
       reflector.v1.k8s.emberstack.com/reflection-auto-enabled: "true"
       reflector.v1.k8s.emberstack.com/reflection-auto-namespaces: "ns1, ns2"
       #
   ```

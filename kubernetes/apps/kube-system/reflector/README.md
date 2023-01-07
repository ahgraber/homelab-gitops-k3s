# [reflector](https://github.com/EmberStack/kubernetes-reflector)

Reflector is a Kubernetes addon designed to monitor changes to resources (secrets and configmaps)
and reflect changes to mirror resources in the same or other namespaces.

## Share secrets across namespaces

Cluster can use `reflector` to copy secrets across namespaces. In particular, this can share the tls
certificates from `networking` to `security`.

- Cert-manager's [faq](https://cert-manager.io/docs/tutorials/syncing-secrets-across-namespaces/)
- [Emberstack Reflector](https://github.com/emberstack/kubernetes-reflector)

`reflector` will check secrets for an annotation indicating it may be replicated to other namespaces

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

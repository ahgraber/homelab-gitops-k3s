# [Cert-Manager](https://cert-manager.io/)

Cert-Manager builds on top of Kubernetes and OpenShift to provide X.509 certificates and issuers as first-class resource types.

## DNS-01 validation

To get a `Certificate`, Cert-Manager creates a `CertificateRequest` that uses an `Issuer` (or `ClusterIssuer`) to
manage the process of creating/managing the cert.

For LetsEncrypt DNS-01 validation, the `Issuer` will create an `Order` and a `Challenge` to validate ownership
of the domain associated with the cert.

We can test this by using the **staging** `Issuer` to provision a test certificate:

```sh
kubectl apply -f ./certificate-test.yaml

# review k8s objects
kubectl get CertificateRequest -n networking
kubectl get Order -n networking
kubectl get Challenge -n networking

# once the DNS challenge has propagated
kubectl get Certificate -n networking
```

## ⚠️ Rate Limits

- [Let's Encrypt rate limits](https://letsencrypt.org/docs/rate-limits/) can be mitigated by testing
  using the `STAGING: 'true'` environmental variable.
- Check on your requests count w/r/t rate limits here: <https://crt.sh/>

## 🔀 Cross-namespace certs

Cluster can use `reflector` to copy secrets across namespaces. In particular, this can share the tls
certificates from `networking` to `security`.

- Cert-manager's [faq](https://cert-manager.io/docs/tutorials/syncing-secrets-across-namespaces/)
- [Emberstack Reflector](https://github.com/emberstack/kubernetes-reflector)

### Process

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

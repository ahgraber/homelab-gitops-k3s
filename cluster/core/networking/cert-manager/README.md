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

# Share secrets across namespaces

Cluster can use `kubed` to copy secrets across namespaces.
In particular, this can share the tls certificates from `networking` to `security`.

* Cert-manager's [faq](https://cert-manager.io/docs/faq/kubed/)
* Kubed's[reference](https://appscode.com/products/kubed/v0.12.0/guides/config-syncer/intra-cluster/)

## Process

1. `kubed` will check secrets for an annotation indicating it may be replicated to other namespaces

   ```yaml
   apiVersion: v1
   kind: Secret
   metadata:
     name: <SECRET_NAME>
     namespace: <SECRET_NAMESPACE>
     annotations:
       kubed.appscode.com/sync: "<SECRET_NAME>=kubed"
   ...
   ```

2. If `kubed` identifies a namespace with a label matching the secret annotation, it will copy and sync the secret from the source namespace

   ```yaml
   apiVersion: v1
   kind: Namespace
   metadata:
     name: <NAMESPACE_NAME>
     labels:
       # Define namespace label for kubed for secrets-sharing -->
       # secret_name: kubed
       <SECRET_NAME>: kubed
   ```

## Example

```yaml
---
apiVersion: v1
kind: Namespace
metadata:
  name: source-ns

---
# secret to replicated
apiVersion: v1
kind: Secret
metadata:
  name: secret_to_copy
  namespace: source-ns
  annotations:
    kubed.appscode.com/sync: "secret_to_copy=kubed" # Sync certificate to matching namespaces
# type: kubernetes.io/tls
data:
  key: 'value'

---
apiVersion: v1
kind: Namespace
metadata:
  name: destination-ns
  labels:
    # Define namespace label for kubed for secrets-sharing -->
    # secret_name: kubed
    secret_to_copy : kubed
```

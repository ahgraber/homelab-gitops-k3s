# [Hammond](https://github.com/akhilrex/hammond)

Hammond is a self hosted vehicle management system to track fuel and other expenses related to all of your vehicles.
It supports multiple users sharing multiple vehicles.
It is the logical successor to Clarkson which has not been updated for quite some time now.

## Secret

From [sample docker-compose.yaml](https://github.com/akhilrex/hammond/blob/master/docker-compose.yml), we require a
secret token.

1. Create secret.sops.yaml:

   ```yaml
   ---
   # yamllint disable
   apiVersion: v1
   kind: Secret
   metadata:
     name: hammond-secret
     namespace: services
     annotations:
       reloader.stakater.com/match: "true"
   stringData:
     JWT_SECRET: < some very strong secret - `openssl rand -base64 36` >
   ```

2. Encrypt secret

   ```sh
   sops --encrypt --in-place ./secrets.sops.yaml
   ```

# New Service Creation

- [New Service Creation](#new-service-creation)
  - [Considerations](#considerations)
  - [General instructions](#general-instructions)
  - [Secret encryption](#secret-encryption)
  - [References](#references)

## Considerations

- If Custom Resources are required, add to ./cluster/crds
- If Secrets are required:

  1. Add to `.envrc` and `direnv allow .`
  2. Add template to ./tmlp
  3. Create & encrypt secret with

  ```sh
  envsubst < ./tmpl/TEMPLATE_NAME.yaml > ./cluster/PATH/TO/DEST.yaml
  sops --encrypt --in-place ./cluster/PATH/TO/DEST.yaml
  ```

## General instructions

- Create folder/subfolder in ./cluster/apps (the difference between `apps` and `core` is that `core`
  does not prune)
  - Include required `helm-release.yaml` or other configuration specifications
  - Include `kustomization.yaml`
- Add pointers to `kustomization.yaml` files in parent dir
- Test-deploy service with `kubectl apply -k <path/to/folder/>
  - _NOTE:_ : services deployed with `kubectl apply` will not have flux's environmental substitutions applied

## Secret encryption

1. Create template file `secret-secretname.sops.yaml.tmpl` which relies on environmental variables from `.envrc`
   to populate secret fields

2. Transform template into yaml

   ```sh
   envsubst < ./path/to/secret-<secretname>.sops.yaml.tmpl >! ./path/to/secret-<secretname>.sops.yaml
   ```

3. Encrypt with sops

   ```sh
   sops --encrypt --in-place ./path/to/secret-<secretname>.sops.yaml
   ```

## References

- [variable substitution](https://github.com/drone/envsubst)

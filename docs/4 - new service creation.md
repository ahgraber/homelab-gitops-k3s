# New Service Creation

## Considerations

* If Custom Resources are required, add to ./cluster/crds
* If Secrets are required:
  1. Add to `.envrc` and `direnv allow .`
  2. Add template to ./tmlp
  3. Create & encrypt secret with

    ```sh
    envsubst < ./tmpl/TEMPLATE_NAME.yaml > ./cluster/PATH/TO/DEST.yaml
    sops --encrypt --in-place ./cluster/PATH/TO/DEST.yaml
    ```

## General instructions

* Create folder/subfolder in ./cluster/apps
  * Include required `helm-release.yaml` or other configuration specifications
  * Include `kustomization.yaml`
* Add pointers to `kustomization.yaml` files in parent dir

## References

* [variable substitution](https://github.com/drone/envsubst)
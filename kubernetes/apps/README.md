# Applications

Applications are defined by a nested folder where the exterior
folder contains a "fluxtomization" (kustomize.toolkit.fluxcd.io/v1) that manages dependencies,
and the inner folder contains a kustomization (kustomize.config.k8s.io/v1beta1) that deploys the manifests.

See `./_app_template/`

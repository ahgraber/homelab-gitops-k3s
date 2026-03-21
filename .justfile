#!/usr/bin/env -S just --justfile

set quiet := true
set shell := ["bash", "-euo", "pipefail", "-c"]
set dotenv-load := true

export KUBECONFIG := justfile_directory() + "/kubeconfig"

mod ansible "ansible"
mod kube "kubernetes"
mod rook "kubernetes/apps/rook-ceph"
mod mlflow "kubernetes/apps/datasci/mlflow"
mod secrets "kubernetes/apps/external-secrets"
mod oauth "kubernetes/apps/security"

[private]
default:
    just --list

# --- Repository ---

[group("repository")]
[doc("Initialize pre-commit hooks")]
hooks:
    pre-commit install --install-hooks

[group("repository")]
[doc("Lint and format with pre-commit")]
lint:
    pre-commit run --all-files

[group("repository")]
[doc("Update repository and pre-commit hooks")]
update:
    git fetch -p
    git pull
    pre-commit autoupdate

[group("repository")]
[confirm("Reset repo to HEAD and clean untracked files?")]
[doc("Reset repo back to HEAD")]
force-reset branch="main":
    git reset --hard HEAD
    git clean -f -d
    git pull origin {{ branch }}

# --- SOPS ---

[group("sops")]
[doc("Initialize Age key for sops")]
age-keygen:
    test -f ./age.key || age-keygen --output ./age.key

[group("sops")]
[doc("Substitute and encrypt sops secret template")]
sops-encode tmpl:
    test -f .sops.yaml
    test -f ./age.key
    [[ "{{ tmpl }}" == *.sops.yaml.tmpl ]]
    unset noclobber
    envsubst < {{ tmpl }} > {{ replace(tmpl, '.tmpl', '') }}
    sops --encrypt --in-place {{ replace(tmpl, '.tmpl', '') }}

[group("sops")]
[doc("Encrypt all Kubernetes sops files not already encrypted")]
sops-encrypt-all:
    test -f .sops.yaml
    test -f ./age.key
    if [ -d ./kubernetes ]; then \
      find ./kubernetes -type f -name '*.sops.*' ! -name '*.tmpl' -exec grep -L 'ENC\[AES256_GCM' {} \; | while IFS= read -r file; do \
        [ -z "$file" ] || sops --encrypt --in-place "$file"; \
      done; \
    fi

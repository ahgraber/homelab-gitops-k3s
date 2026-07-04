set quiet := true
set shell := ["bash", "-euo", "pipefail", "-c"]

[private]
default:
    just --list db

[group("db")]
[doc("Hibernate a CNPG database")]
hibernate cnpg ns="default":
    kubectl annotate cluster {{ cnpg }} -n {{ ns }} --overwrite cnpg.io/hibernation=on

[group("db")]
[doc("Hibernate all CNPG databases")]
hibernate-all:
    kubectl get cluster --all-namespaces --no-headers | while read -r ns name _; do \
      kubectl annotate cluster "$name" -n "$ns" --overwrite cnpg.io/hibernation=on; \
    done

[group("db")]
[doc("Resume a CNPG database")]
resume cnpg ns="default":
    kubectl annotate cluster {{ cnpg }} -n {{ ns }} cnpg.io/hibernation-

[group("db")]
[doc("Resume all CNPG databases")]
resume-all:
    kubectl get cluster --all-namespaces --no-headers | while read -r ns name _; do \
      kubectl annotate cluster "$name" -n "$ns" cnpg.io/hibernation-; \
    done

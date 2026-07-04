set quiet := true
set shell := ["bash", "-euo", "pipefail", "-c"]

volsync_dir := source_directory()
volsync_scripts_dir := volsync_dir + "/scripts"
volsync_templates_dir := volsync_scripts_dir + "/templates"

[private]
default:
    just --list volsync

[group("volsync")]
[doc("Calculate relative path from one file to volsync components")]
relpath start end="./kubernetes/components/volsync":
    test -f {{ start }}
    test -d {{ end }}
    realpath --relative-to="$(dirname {{ start }})" "{{ end }}"

[group("volsync")]
[doc("List restic snapshots for a ReplicationSource")]
list app ns="default":
    ts=$(date +%H%M%S); \
    export app='{{ app }}' ns='{{ ns }}' ts="$ts"; \
    envsubst < '{{ volsync_templates_dir }}/ListJob.tmpl.yaml' | kubectl apply -f -; \
    bash '{{ volsync_scripts_dir }}/wait-for-job.sh' "list-{{ app }}-$ts" '{{ ns }}'; \
    kubectl -n '{{ ns }}' wait job/list-{{ app }}-$ts --for condition=complete --timeout=1m; \
    kubectl -n '{{ ns }}' logs job/list-{{ app }}-$ts --container list; \
    kubectl -n '{{ ns }}' delete job list-{{ app }}-$ts

[group("volsync")]
[doc("Unlock restic repository for a ReplicationSource")]
unlock app ns="default":
    ts=$(date +%H%M%S); \
    export app='{{ app }}' ns='{{ ns }}' ts="$ts"; \
    envsubst < '{{ volsync_templates_dir }}/UnlockJob.tmpl.yaml' | kubectl apply -f -; \
    bash '{{ volsync_scripts_dir }}/wait-for-job.sh' "unlock-{{ app }}-$ts" '{{ ns }}'; \
    kubectl -n '{{ ns }}' wait job/unlock-{{ app }}-$ts --for condition=complete --timeout=1m; \
    kubectl -n '{{ ns }}' logs job/unlock-{{ app }}-$ts --container unlock; \
    kubectl -n '{{ ns }}' delete job unlock-{{ app }}-$ts

[group("volsync")]
[doc("Trigger a restic ReplicationSource snapshot")]
snapshot app ns="default":
    kubectl -n '{{ ns }}' get replicationsources {{ app }} >/dev/null
    kubectl -n '{{ ns }}' patch replicationsources {{ app }} --type merge \
      -p '{"spec":{"trigger":{"manual":"'"$(date +%H%M%S)"'"}}}'
    bash '{{ volsync_scripts_dir }}/wait-for-job.sh' volsync-src-{{ app }} '{{ ns }}'
    kubectl -n '{{ ns }}' wait job/volsync-src-{{ app }} --for condition=complete --timeout=120m

[group("volsync")]
[doc("Restore a ReplicationSource from a restic snapshot")]
restore app ns="default" previous="2":
    bash '{{ volsync_scripts_dir }}/restore.sh' '{{ app }}' '{{ ns }}' '{{ previous }}'

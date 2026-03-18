set quiet := true
set shell := ["bash", "-euo", "pipefail", "-c"]

ansible_dir := justfile_directory()
ansible_cfg := "ANSIBLE_CONFIG=" + ansible_dir + "/ansible.cfg"
inventory := ansible_dir + "/inventory"

[private]
default:
    just --list ansible

[doc("Install Ansible with uv")]
install:
    reqs_file="{{ ansible_dir }}/requirements.txt"; \
    extra_args=(); \
    while IFS= read -r line; do \
      [ -z "${line}" ] && continue; \
      case "${line}" in \#*) continue ;; esac; \
      extra_args+=(--with "${line}"); \
    done < "${reqs_file}"; \
    if [ ${#extra_args[@]} -gt 0 ]; then \
      uv tool install --force --with-executables-from ansible-core,ansible-lint "${extra_args[@]}" ansible; \
    else \
      uv tool install --force --with-executables-from ansible-core,ansible-lint ansible; \
    fi
    ansible-galaxy install --force --role-file "{{ ansible_dir }}/requirements.yaml"

[doc("List all the hosts in inventory")]
hosts:
    {{ ansible_cfg }} ansible all -i '{{ inventory }}' --list-hosts

[doc("Ping hosts")]
ping group="kubernetes":
    {{ ansible_cfg }} ansible -i '{{ inventory }}' {{ group }} --one-line -m ping

[doc("Uptime of hosts")]
uptime group="kubernetes":
    {{ ansible_cfg }} ansible -i '{{ inventory }}' {{ group }} --one-line -a uptime

[doc("Prepare nodes for k3s")]
prepare group="kubernetes":
    {{ ansible_cfg }} ansible-playbook -i '{{ inventory }}' -l {{ group }} '{{ ansible_dir }}/playbooks/k3s-prepare.yaml' --become

[doc("Clean up node cruft on k3s nodes")]
k3s-cleanup group="kubernetes":
    {{ ansible_cfg }} ansible-playbook -i '{{ inventory }}' -l {{ group }} '{{ ansible_dir }}/playbooks/node-cruft-cleanup.yaml' --become

[doc("List all available Ansible playbooks")]
list:
    find '{{ ansible_dir }}/playbooks' -maxdepth 1 -type f \( -name '*.yaml' -o -name '*.yml' \) -exec basename {} \; | sort

[doc("Run an Ansible playbook by name")]
playbook playbook group="kubernetes" *args:
    {{ ansible_cfg }} ansible-playbook -i '{{ inventory }}' -l {{ group }} '{{ ansible_dir }}/playbooks/{{ playbook }}.yaml' {{ args }}

[doc("Run an arbitrary command on hosts")]
cmd cmd group="kubernetes" *args:
    {{ ansible_cfg }} ansible -i '{{ inventory }}' {{ group }} -m ansible.builtin.shell -a "{{ cmd }}" {{ args }}

[doc("Shut down the cluster")]
shutdown group="kubernetes":
    {{ ansible_cfg }} ansible-playbook -i '{{ inventory }}' -l {{ group }} '{{ ansible_dir }}/playbooks/k3s-stop.yaml' --become
    {{ ansible_cfg }} ansible -i '{{ inventory }}' {{ group }} -m ansible.builtin.shell -a 'shutdown now' --become

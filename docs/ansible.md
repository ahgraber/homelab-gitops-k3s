# Ansible

- [Ansible](#ansible)
  - [Call arbitrary playbooks](#call-arbitrary-playbooks)
    - [With ansible](#with-ansible)
    - [With just](#with-just)
  - [Send arbitrary commands](#send-arbitrary-commands)
    - [With ansible](#with-ansible-1)
    - [With just](#with-just-1)

## Call arbitrary playbooks

### With ansible

```sh
# paths assume running from /ansible dir
cd ./ansible
ansible-playbook -i <path/to/inventory> -l <groupname> <path/to/playbook> --become
# e.g.
# > ansible-playbook -i ./inventory -l ubuntu ./playbooks/cluster-reboot.yaml --become
```

### With just

```sh
just ansible playbook k3s-reboot kubernetes -- --become
```

## Send arbitrary commands

### With ansible

```sh
# paths assume running from /ansible dir
cd ./ansible
ansible -i <path/to/inventory> -l <groupname> -m ansible.builtin.shell -a <shell command> --become
# e.g.
# > ansible -i ./inventory -l <groupname> -m ansible.builtin.shell -a "apt upgrade -y" --become
```

### With just

```sh
just ansible cmd "apt upgrade -y" kubernetes -- --become
```

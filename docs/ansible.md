# Ansible

- [Ansible](#ansible)
  - [Call arbitrary playbooks](#call-arbitrary-playbooks)
    - [With ansible](#with-ansible)
    - [With task](#with-task)
  - [Send arbitrary commands](#send-arbitrary-commands)
    - [With ansible](#with-ansible-1)
    - [With task](#with-task-1)

## Call arbitrary playbooks

### With ansible

```sh
# paths assume running from /ansible dir
cd ./ansible
ansible-playbook -i <path/to/inventory> -l <groupname> <path/to/playbook> --become
# e.g.
# > ansible-playbook -i ./inventory -l ubuntu ./playbooks/cluster-reboot.yaml --become
```

### With task

```sh
task ansible:run group='kubernetes' playbook='k3s-reboot' -- '--become'
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

### With task

```sh
task ansible:cmd group='kubernetes' cmd='apt upgrade -y' -- '--become'
```

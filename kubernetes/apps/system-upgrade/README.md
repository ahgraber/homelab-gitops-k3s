# [system-upgrade-controller](https://github.com/rancher/system-upgrade-controller)

Provides a kubernetes-native way to manage host node upgrades.

## Notes

- Manual drain and restart of k3s may be necessary

  ```sh
  # from admin
  kubectl drain <node> --delete-emptydir-data --ignore-daemonsets --force
  ```

  ```sh
  # from k3s node
  sudo systemctl k3s stop
  sudo systemctl k3s start
  ```

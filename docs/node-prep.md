<!-- markdownlint-disable MD013 -->
# 💻 Machine Preparation

## System requirements

📍 _k3s default behaviour is that all nodes are able to run workloads, including control nodes. Worker nodes are therefore optional._

📍 _If you have 3 or more nodes it is strongly recommended to make 3 of them control nodes for a highly available control plane._

📍 _Ideally you will run the cluster on bare metal machines._

| Role    | Cores    | Memory        | System Disk               |
|---------|----------|---------------|---------------------------|
| Control | 4 _(6*)_ | 8GB _(24GB*)_ | 100GB _(500GB*)_ SSD/NVMe |
| Worker  | 4 _(6*)_ | 8GB _(24GB*)_ | 100GB _(500GB*)_ SSD/NVMe |
| _\* recommended_ ||||

## Debian for AMD64

1. Download the latest stable release of Debian from [here](https://cdimage.debian.org/debian-cd/current/amd64/iso-dvd), then follow [this guide](https://www.linuxtechi.com/how-to-install-debian-12-step-by-step) to get it installed.

   Deviations from the guide:

   > ```txt
   > Choose "Guided - use entire disk"
   > Choose "All files in one partition"
   > Delete Swap partition
   > Uncheck all Debian desktop environment options
   > ```

2. [Post install] Remove CD/DVD as apt source

    ```sh
    su -
    sed -i '/deb cdrom/d' /etc/apt/sources.list
    apt update
    exit
    ```

3. [Post install] Enable sudo for your non-root user

    ```sh
    su -
    apt update
    apt install -y sudo
    usermod -aG sudo ${username}
    echo "${username} ALL=(ALL) NOPASSWD:ALL" | tee /etc/sudoers.d/${username}
    exit
    newgrp sudo
    sudo apt update
    ```

4. [Post install] Add SSH keys (or use `ssh-copy-id` on the client that is connecting)

   a. Add with `ssh-copy-id`

      ```sh
      ssh-copy-id -i ~/.ssh/id_ed25519 <user>@<host>
      ```

   b. Add with github

      📍 _First make sure your ssh keys are up-to-date and added to your github account as [instructed](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account)._

      ```sh
      mkdir -m 700 ~/.ssh
      sudo apt install -y curl
      curl https://github.com/${github_username}.keys > ~/.ssh/authorized_keys
      chmod 600 ~/.ssh/authorized_keys
      ```

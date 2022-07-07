# :memo:&nbsp; Prerequisites

- [:memo:&nbsp; Prerequisites](#memo-prerequisites)
  - [:computer:&nbsp; Nodes](#computer-nodes)
  - [:wrench:&nbsp; Tools](#wrench-tools)
  - [:ballot_box_with_check:&nbsp; Installation](#ballot_box_with_check-installation)
  - [:warning:&nbsp; pre-commit](#warning-pre-commit)
  - [:bulb:&nbsp; direnv](#bulb-direnv)
  - [:bulb:&nbsp; SOPS](#bulb-sops)
  - [:closed_lock_with_key:&nbsp; Set up Age](#closed_lock_with_key-set-up-age)
    - [1. Create a Age Private / Public Key](#1-create-a-age-private--public-key)
    - [2. Set up the directory for the Age key and move the Age file to it](#2-set-up-the-directory-for-the-age-key-and-move-the-age-file-to-it)
    - [3. Add the Age key file and public key to the local `.envrc` and reload](#3-add-the-age-key-file-and-public-key-to-the-local-envrc-and-reload)

## :computer:&nbsp; Nodes

Already provisioned Bare metal or VMs with any modern operating system like Ubuntu, Debian or
CentOS.

## :wrench:&nbsp; Tools

:round_pushpin: You need to install the required CLI tools listed below on your workstation.

| Tool                                                               | Purpose                                                             |
| ------------------------------------------------------------------ | ------------------------------------------------------------------- |
| [ansible](https://www.ansible.com)                                 | Automate actions against nodes (like installing k3s)                |
| [kubectl](https://kubernetes.io/docs/tasks/tools/)                 | Allows you to run commands against Kubernetes clusters              |
| [flux](https://toolkit.fluxcd.io/)                                 | Operator that manages your k8s cluster based on your Git repository |
| [age](https://github.com/FiloSottile/age)                          | A simple, modern and secure encryption tool (and Go library)        |
| [SOPS](https://github.com/mozilla/sops)                            | Encrypts k8s secrets with GnuPG                                     |
| [direnv](https://github.com/direnv/direnv)                         | Exports env vars based on present working directory                 |
| [jq](https://stedolan.github.io/jq/)                               | Parse and edit json                                                 |
| [pre-commit](https://github.com/pre-commit/pre-commit)             | Runs checks during `git commit`                                     |
| [gitleaks](https://github.com/zricethezav/gitleaks)                | Scan git repos (or files) for secrets                               |
| [kustomize](https://kustomize.io/)                                 | Template-free way to customize application configuration            |
| [helm](https://helm.sh/)                                           | Manage Kubernetes applications                                      |
| [k9s](https://k9scli.io/)                                          | CLI-GUI for k8s clusters                                            |
| [popeye](https://popeyecli.io/)                                    | CLI-based scanner/finder for k8s clusters                           |
| [kubetail](https://github.com/johanhaleby/kubetail)                | aggregate (tail/follow) logs from multiple pods into one            |
| [krew](https://krew.sigs.k8s.io/)                                  | plugin manager for kubectl command-line tool                        |

## :ballot_box_with_check:&nbsp; Installation

```sh
# install packages
brew install age direnv flux gitleaks go helm jq kompose kubernetes-cli kustomize pre-commit sops

# if Ansible not installed
conda create --name ansible && conda activate ansible
conda install ansible --name ansible
```

## :warning:&nbsp; pre-commit

It is advisable to install [pre-commit](https://pre-commit.com/) and the pre-commit hooks that come
with this repository. [sops-pre-commit](https://github.com/k8s-at-home/sops-pre-commit) will check
to make sure you are not by accident commiting your secrets un-encrypted.

After pre-commit is installed on your machine run:

```sh
pre-commit install && pre-commit autoupdate
```

## :bulb:&nbsp; direnv

It is advisable to install [direnv](https://github.com/direnv/direnv) to persist environmental
variables to a hidden `.envrc` file.

After direnv is installed, set up on the local repo path:

```sh
# add direnv hooks
echo 'eval "$(direnv hook zsh)"' >> ~/.zshrc
source ~/.zshrc

# add .envrc and .env to gitignores (global, local)
git config --global core.excludesFile '~/.gitignore'
touch ~/.gitignore
echo '.envrc' >> ~/.gitignore
echo '.env' >> ~/.gitignore
echo '.envrc' >> .gitignore
echo '.env' >> .gitignore

# remove .gitignored files
git ls-files -i --exclude-from=.gitignore | xargs git rm --cached

# set up direnv config to whitelist folders for direnv
mkdir -p ~/.config/direnv
echo > direnv.toml << EOF
[whitelist]
prefix = [ "/path/to/folders/to/whitelist" ]
exact = [ "/path/to/envrc/to/whitelist" ]
EOF

direnv reload
```

## :bulb:&nbsp; SOPS

The [SOPS VSCode Extension](https://github.com/signageos/vscode-sops) will automatically decrypt you
SOPS secrets when you click on the file in the editor and encrypt them when you save and exit the
file.

## :closed_lock_with_key:&nbsp; Set up Age

:round_pushpin: Here we will create a Age Private and Public key. Using SOPS with Age allows us to encrypt and decrypt secrets.

### 1. Create a Age Private / Public Key

```sh
age-keygen -o age.agekey
```

### 2. Set up the directory for the Age key and move the Age file to it

```sh
# mac
mkdir -p "${HOME}/Library/Application Support/sops/age"
mv age.agekey "${HOME}/Library/Application Support/sops/age/keys.txt"
# linux
mkdir -p "${HOME}/.config/sops/age/keys.txt"
mv age.agekey "${HOME}/.config/sops/age/keys.txt"
```

### 3. Add the Age key file and public key to the local `.envrc` and reload

```sh
echo "export SOPS_AGE_KEY_FILE=(expand_path ${HOME}/.config/sops/age/keys.txt) >> .envrc
echo "export AGE_PUBLIC_KEY=\"$(grep public """${HOME}/.config/sops/age/keys.txt""" | awk '{ print $NF }')\"" >> .envrc
direnv allow .
```

_Optional:_ Save keys to password manager or vault

> _**Don't forget to delete the keys from the repo once saved elsewhere!!!**_

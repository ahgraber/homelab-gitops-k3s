# 📝 Prerequisites

- [📝 Prerequisites](#-prerequisites)
  - [💻 Nodes](#-nodes)
  - [🛠 Tools](#-tools)
  - [📝 Installation](#-installation)
  - [✅ Set up go-task](#-set-up-go-task)
  - [⚠️ Activate pre-commit](#️-activate-pre-commit)
  - [💡 direnv](#-direnv)
  - [💡 SOPS](#-sops)
  - [🔐 Set up Age](#-set-up-age)

## 💻 Nodes

Provisioned with [pxe, ansible, and/or terraform](https://github.com/ahgraber/homelab-infra).

## 🛠 Tools

| Tool                                                               | Purpose                                                             |
| ------------------------------------------------------------------ | ------------------------------------------------------------------- |
| [ansible](https://www.ansible.com)                                 | Automate actions against nodes (like installing k3s)                |
| [kubectl](https://kubernetes.io/docs/tasks/tools/)                 | Allows you to run commands against Kubernetes clusters              |
| [kustomize](https://kustomize.io/)                                 | Template-free way to customize application configuration            |
| [helm](https://helm.sh/)                                           | Package manager for Kubernetes                                      |
| [flux](https://toolkit.fluxcd.io/)                                 | Operator that manages your k8s cluster based on your Git repository |
| [age](https://github.com/FiloSottile/age)                          | A simple, modern and secure encryption tool (and Go library)        |
| [SOPS](https://github.com/mozilla/sops)                            | Encrypts k8s secrets with GnuPG                                     |
| [direnv](https://github.com/direnv/direnv)                         | Exports env vars based on present working directory                 |
| [jq](https://stedolan.github.io/jq/)                               | Parse and edit json                                                 |
| [yq](https://github.com/mikefarah/yq)                              | Parse and edit yaml                                                 |
| [pre-commit](https://github.com/pre-commit/pre-commit)             | Runs checks during `git commit`                                     |
| [gitleaks](https://github.com/zricethezav/gitleaks)                | Scan git repos (or files) for secrets                               |
| [k9s](https://k9scli.io/)                                          | CLI-GUI for k8s clusters                                            |
| [stern](https://github.com/stern/stern)                            | Multi pod and container log tailing for Kubernetes                  |
| [task](https://github.com/go-task/task)                            | A task runner / simpler Make alternative                            |
| [terraform](https://www.terraform.io/)                             | Infra as code provisioner                                           |
| [weave gitops](https://docs.gitops.weave.works/docs/intro/)        | Flux extension for gitops                                           |

## 📝 Installation

## ✅ Set up [go-task](https://github.com/go-task/task)

This repo uses task as a framework for setting things up.

```sh
brew install go-task/tap/go-task
# install tools & utilities
task init
```

## ⚠️ Activate pre-commit

[pre-commit](https://pre-commit.com/) is installed with `task init`.
[sops-pre-commit](https://github.com/k8s-at-home/sops-pre-commit) will check
to make sure you are not by accident committing your secrets un-encrypted.

```sh
pre-commit install && pre-commit autoupdate
```

## 💡 direnv

[direnv](https://github.com/direnv/direnv) allows persisting environmental
variables to a hidden `.envrc` file.

After direnv is installed with `task init`, set up on the local repo path:

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

## 💡 SOPS

The [SOPS VSCode Extension](https://github.com/signageos/vscode-sops) will automatically decrypt you
SOPS secrets when you click on the file in the editor and encrypt them when you save and exit the
file.

## 🔐 Set up Age

:round_pushpin: Here we will create a Age Private and Public key. Using SOPS with Age allows us to encrypt and decrypt secrets.

1. Create a Age Private / Public Key

   ```sh
   age-keygen -o age.agekey
   ```

2. Set up the directory for the Age key and move the Age file to it

   ```sh
   # mac
   mkdir -p "${HOME}/Library/Application Support/sops/age"
   mv age.agekey "${HOME}/Library/Application Support/sops/age/keys.txt"
   # linux
   mkdir -p "${HOME}/.config/sops/age/keys.txt"
   mv age.agekey "${HOME}/.config/sops/age/keys.txt"
   ```

3. Add the Age key file and public key to the local `.envrc` and reload

   ```sh
   echo "export SOPS_AGE_KEY_FILE=(expand_path ${HOME}/.config/sops/age/keys.txt) >> .envrc
   echo "export AGE_PUBLIC_KEY=\"$(grep public """${HOME}/.config/sops/age/keys.txt""" | awk '{ print $NF }')\"" >> .envrc
   direnv allow .
   ```

   _Optional:_ Save keys to password manager or vault
   _**Don't forget to delete the keys from the repo once saved elsewhere!!!**_

# :memo:&nbsp; Prerequisites

## :computer:&nbsp; Nodes

Already provisioned Bare metal or VMs with any modern operating system like
Ubuntu, Debian or CentOS.

## :wrench:&nbsp; Tools

:round_pushpin: You need to install the required CLI tools listed below
on your workstation.

| Tool                                                               | Purpose                                                             | Minimum version | Required |
|--------------------------------------------------------------------|---------------------------------------------------------------------|:---------------:|:--------:|
| [k3sup](https://github.com/alexellis/k3sup)                        | Tool to install k3s on your nodes                                   |    `0.10.2`     |    ✅     |
| [kubectl](https://kubernetes.io/docs/tasks/tools/)                 | Allows you to run commands against Kubernetes clusters              |    `1.21.0`     |    ✅     |
| [flux](https://toolkit.fluxcd.io/)                                 | Operator that manages your k8s cluster based on your Git repository |    `0.12.3`     |    ✅     |
| [SOPS](https://github.com/mozilla/sops)                            | Encrypts k8s secrets with GnuPG                                     |     `3.7.1`     |    ✅     |
| [GnuPG](https://gnupg.org/)                                        | Encrypts and signs your data                                        |    `2.2.27`     |    ✅     |
| [pinentry](https://gnupg.org/related_software/pinentry/index.html) | Allows GnuPG to read passphrases and PIN numbers                    |     `1.1.1`     |    ✅     |
| [direnv](https://github.com/direnv/direnv)                         | Exports env vars based on present working directory                 |    `2.28.0`     |    ❌     |
| [pre-commit](https://github.com/pre-commit/pre-commit)             | Runs checks during `git commit`                                     |    `2.12.0`     |    ❌     |
| [kustomize](https://kustomize.io/)                                 | Template-free way to customize application configuration            |     `4.1.0`     |    ❌     |
| [helm](https://helm.sh/)                                           | Manage Kubernetes applications                                      |     `3.5.4`     |    ❌     |

## :ballot_box_with_check:&nbsp; Installation

```sh
# install k3sup
curl -sLS https://get.k3sup.dev | sh
sudo install k3sup /usr/local/bin/

# install other packages
brew install direnv flux helm jq kompose kubernetes-cli kustomize pre-commit sops

# if GPGTools not installed
brew install gnupg
```

## :warning:&nbsp; pre-commit

It is advisable to install [pre-commit](https://pre-commit.com/) and the pre-commit hooks that come with this repository.
[sops-pre-commit](https://github.com/k8s-at-home/sops-pre-commit) will check to make sure you are not by accident commiting your secrets un-encrypted.

After pre-commit is installed on your machine run:

```sh
pre-commit install-hooks
```

## :bulb:&nbsp; direnv

It is advisable to install [direnv](https://github.com/direnv/direnv)
to persist environmental variables to a hidden `.envrc` file.

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
echo > direnv.toml <<EOF
[whitelist]
prefix = [ "/path/to/folders/to/whitelist" ]
exact = [ "/path/to/envrc/to/whitelist" ]
EOF

direnv reload
```

## :bulb:&nbsp; SOPS

The [SOPS VSCode Extension](https://github.com/signageos/vscode-sops)
will auto-decrypt files locally

## :closed_lock_with_key:&nbsp; Set up GnuPG keys

:round_pushpin: Here we will create a personal and a Flux GPG key.
Using SOPS with GnuPG allows us to encrypt and decrypt secrets.

## 1. Create a Personal GPG Key, password protected, and export the fingerprint. It's **strongly encouraged** to back up this key somewhere safe so you don't lose it

```sh
# add environmental variables to .envrc for direnv
export EMAIL=""
export FNAME=""
export LNAME=""
echo "export EMAIL=\"${EMAIL}\"" >> .envrc
echo "export PERSONAL_KEY_NAME=\"${FNAME} ${LNAME} ${EMAIL}\"" >> .envrc

export GPG_TTY=$(tty)
gpg --batch --full-generate-key <<EOF
Key-Type: 1
Key-Length: 4096
Subkey-Type: 1
Subkey-Length: 4096
Expire-Date: 0
Name-Real: ${PERSONAL_KEY_NAME}
EOF

gpg --list-secret-keys "${PERSONAL_KEY_NAME}"
# pub   rsa4096 2021-03-11 [SC]
#       772154FFF783DE317KLCA0EC77149AC618D75581
# uid           [ultimate] k8s@home (Macbook) <k8s-at-home@gmail.com>
# sub   rsa4096 2021-03-11 [E]

# replace key value from output above
# export PERSONAL_KEY_FP=772154FFF783DE317KLCA0EC77149AC618D75581
echo "export PERSONAL_KEY_FP=\"$(gpg --list-secret-keys ${PERSONAL_KEY_NAME} | sed -n '2p' | xargs)\"" >> .envrc
```

## 2. Create a Flux GPG Key and export the fingerprint

```sh
export CLUSTERNAME=""
echo "export FLUX_KEY_NAME=\"${CLUSTERNAME} (Flux) ${EMAIL}\"" >> .envrc

export GPG_TTY=$(tty)
gpg --batch --full-generate-key <<EOF
%no-protection
Key-Type: 1
Key-Length: 4096
Subkey-Type: 1
Subkey-Length: 4096
Expire-Date: 0
Name-Real: ${FLUX_KEY_NAME}
EOF

gpg --list-secret-keys "${FLUX_KEY_NAME}"
# pub   rsa4096 2021-03-11 [SC]
#       AB675CE4CC64251G3S9AE1DAA88ARRTY2C009E2D
# uid           [ultimate] Home cluster (Flux) <k8s-at-home@gmail.com>
# sub   rsa4096 2021-03-11 [E]

# replace key value from output above
# export FLUX_KEY_FP=AB675CE4CC64251G3S9AE1DAA88ARRTY2C009E2D
echo "export FLUX_KEY_FP=\"$(gpg --list-secret-keys ${FLUX_KEY_NAME} | sed -n '2p' | xargs)\"" >> .envrc
```

## 3. Save keys to password manager or vault

```sh
gpg --output backup-key-personal.pgp --armor --export-secret-keys --export-options export-backup ${PERSONAL_KEY_NAME}
gpg --output backup-key-flux.pgp --armor --export-secret-keys --export-options export-backup ${FLUX_KEY_NAME}
```

_**Don't forget to delete the keys from the repo once saved elsewhere!!!**_

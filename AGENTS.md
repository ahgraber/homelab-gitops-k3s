# Repository Guidelines for AI Agents

This document provides essential context and instructions for AI agents working on this homelab Kubernetes cluster repository.

## Project Overview

This is a GitOps-managed homelab Kubernetes cluster using:

- **k3s**: Lightweight Kubernetes distribution
- **Flux CD**: GitOps continuous delivery tool
- **Ansible**: Node preparation and cluster installation
- **SOPS + Age**: Secrets encryption

The repository is the single source of truth.
Changes committed here are automatically applied to the cluster by Flux.

## Repository Structure

```text
.
├── ansible/              # Ansible playbooks and inventory for node/cluster management
│   ├── inventory/       # Host definitions and variables (includes SOPS-encrypted secrets)
│   ├── playbooks/       # Playbooks for cluster operations
│   └── roles/           # Ansible roles (including xanmanning.k3s)
├── kubernetes/          # Kubernetes manifests and Flux configuration
│   ├── apps/           # Applications organized by namespace
│   │   └── <namespace>/<app>/  # Each app has its own directory with README.md
│   ├── bootstrap/      # Initial cluster secrets (SOPS-encrypted)
│   ├── flux/           # Flux configuration and app definitions
│   └── templates/      # Reusable templates (e.g., volsync)
├── scripts/            # Utility scripts (bash with shellcheck, python with uv/ruff)
├── docs/               # Human-readable documentation
└── .taskfiles/         # Task definitions (reference only - see Command Execution)
```

## Nix Development Environment

This repository uses Nix flakes to provide a consistent development environment with all required tools (kubectl, flux, helm, sops, etc.).

### Running Commands with Nix

Use the `nix develop` wrapper to run commands with the correct tools and kubeconfig:

```bash
nix develop -c env 'KUBECONFIG=./kubeconfig' <command>
```

If running with `nix develop` fails, add `--extra-experimental-features` flags:

```bash
nix --extra-experimental-features 'nix-command flakes' develop -c env 'KUBECONFIG=./kubeconfig' <command>
```

Examples:

```bash
# kubectl commands
nix develop -c env 'KUBECONFIG=./kubeconfig' kubectl get pods -n network

# flux commands
nix develop -c env 'KUBECONFIG=./kubeconfig' flux get hr -A
```

## Command Execution Patterns

**IMPORTANT**: Do NOT use `task` commands directly.
Task is a convenience tool for humans.

Instead:

1. **Reference the Taskfiles** (`.taskfiles/`) to understand what commands should be run
2. **Execute the underlying commands** using the nix develop wrapper with `kubectl`, `flux`, `ansible`, `sops`, etc.

Example:

- ❌ Don't run: `task flux:bootstrap`

- ✅ Do: Look at `.taskfiles/flux/taskfile.yaml` to see the actual command, then run:

  ```bash
  nix develop -c env 'KUBECONFIG=./kubeconfig' \
    flux bootstrap github \
    --owner=ahgraber \
    --repository=homelab-gitops-k3s \
    --branch=main \
    --path=kubernetes/flux
  ```

This ensures your commands work even if the Taskfile abstractions change.

## Kubectl and Flux Operations

- **Use nix develop wrapper**: All kubectl/flux commands should use the nix develop pattern:

  ```bash
  nix develop -c env 'KUBECONFIG=./kubeconfig' <command>
  ```

  For additional usage directives and security constraints, see [.codex/rules/kubectl.rules](.codex/rules/kubectl.rules).

### Security Rules

**CRITICAL**: Agents must never access secret contents.
Listing secret names is allowed, but retrieving secret data is forbidden:

- ✅ `kubectl get secret` or `kubectl get secrets` (without output flags) - lists secret names
- ❌ `kubectl get secret/secrets` with any output flags (`-o`, `--output`, `-ojson`, `-oyaml`, etc.)
- ❌ `kubectl get externalsecret/clustersecretstore/secretstore` with output flags
- ❌ Any template or jsonpath queries on secret resources

**Allowed kubectl operations** (read-only, informational):

- ✅ `kubectl get` (without output flags)
- ✅ `kubectl describe`
- ✅ `kubectl logs`
- ✅ `kubectl top`
- ✅ `kubectl events`
- ✅ `kubectl api-resources`, `kubectl api-versions`
- ✅ `kubectl cluster-info`, `kubectl version`, `kubectl explain`

**Allowed flux operations**:

- ✅ `flux get` (sources, kustomizations, helmreleases)
- ✅ `flux logs`, `flux check`, `flux tree`, `flux trace`

### Command Syntax

- Informational queries (get, describe, logs, events, etc.) are permitted; avoid destructive actions unless explicitly requested.

- Command ordering follows the prefix-based ruleset: `<command> <verb> <type> [output flags] [other flags] -n <namespace> [name]`.
  Keep the resource type immediately after the verb and put namespace flags last so output-format flags (`-o/--output`) stay adjacent to the type for secret-safety controls.

- Examples with ordering:

  ```bash
  nix develop -c env 'KUBECONFIG=./kubeconfig' kubectl get pods -n <namespace>
  nix develop -c env 'KUBECONFIG=./kubeconfig' kubectl get pod <name> -n <namespace>
  nix develop -c env 'KUBECONFIG=./kubeconfig' kubectl logs -n <namespace> <pod>
  nix develop -c env 'KUBECONFIG=./kubeconfig' flux get hr -n <namespace>
  ```

- Keep commands scoped and explicit; do not rely on default namespaces or contexts when fetching cluster state.

## Networking Architecture

Understanding the networking stack is critical for configuring ingress correctly.

### Network Components

#### Cilium (CNI)

- Provides pod networking and network policies
- Replaces kube-proxy with eBPF-based routing
- Handles service mesh features

#### kube-vip

- Provides high-availability VIP for the control plane
- Manages the cluster API endpoint

#### k8s-gateway

- Provides internal DNS resolution for cluster services
- Resolves `*.domain.com` queries from internal network
- Requires split DNS configuration on home DNS server (e.g., Pi-hole)

#### Envoy Gateway (Internal)

- Ingress class: `internal`
- For services that should only be accessible within the home network
- Examples: Hubble UI, internal dashboards, home automation
- Does NOT route through Cloudflare

#### Envoy Gateway (External)

- Ingress class: `external`
- For services that need to be accessible from the internet
- Routes through Cloudflare Tunnel for security
- Requires external-dns annotation for DNS record creation

#### Cloudflare Tunnel

- Secure tunnel from Cloudflare edge to the cluster
- No exposed ports on home network
- Provides WAF and DDoS protection

#### external-dns

- Automatically manages DNS records in Cloudflare
- Reads ingress annotations to create/update DNS entries
- Watches for `external` ingress class resources

#### cert-manager

- Provides TLS certificates via Let's Encrypt
- Supports both staging and production environments
- Uses Cloudflare DNS challenge for wildcard certificates

### Choosing the Right Ingress Pattern

For internal-only services:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: my-internal-app
spec:
  parentRefs:
    - name: internal
      namespace: network
      sectionName: https
```

For publicly accessible services:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: my-public-app
  annotations:
    external-dns.alpha.kubernetes.io/target: external.<domain>
spec:
  parentRefs:
    - name: external
      namespace: network
      sectionName: https
```

## Application Development Workflow

### BEFORE Modifying Any Existing App

1. **Read the app's README.md**: `kubernetes/apps/<namespace>/<app>/README.md`
2. **Read the app's upstream documentation**: Helm chart docs, official docs
3. **Understand dependencies**: Check what other apps this depends on
4. **Review current configuration**: Look at HelmRelease values and customizations

### WHEN Adding a New App

Required structure:

```text
kubernetes/apps/<namespace>/<app>/
├── README.md                    # MANDATORY - Document the app
├── ks.yaml                      # Flux Kustomization for this app
└── app/
    ├── kustomization.yaml
    ├── helmrelease.yaml         # Or raw manifests
    └── *.sops.yaml             # Encrypted secrets if needed
```

README.md must include:

- Purpose and description of the app
- Configuration details and important settings
- Dependencies (other apps, infrastructure requirements)
- Known issues or gotchas
- Links to upstream documentation

#### Steps

1. Research the application and read its official documentation
2. Create the directory structure
3. Write the README.md first
4. Create HelmRelease or manifests following existing patterns
5. Add to `kubernetes/flux/apps.yaml` if needed
6. Test with: `flux get hr -n <namespace> <app>`

### WHEN Modifying Existing Apps

1. Always read and update the README.md if configuration changes
2. Test changes don't break dependencies
3. Verify Flux reconciliation after changes
4. Document any new gotchas discovered

## Secret Management (CRITICAL)

**SECURITY BOUNDARY**: All secrets must be encrypted with SOPS.

### Rules

- ✅ All `*.sops.yaml` files MUST be encrypted with SOPS
- ❌ NEVER commit unencrypted secrets
- ✅ ALWAYS verify encryption before `git push`
- ✅ Use Age encryption (not PGP)

### Environment Variables

```bash
export SOPS_AGE_KEY_FILE="$HOME/.config/sops/age/keys.txt"  # or age.key in repo root
export AGE_PUBLIC_KEY="age1..."  # Public key for encryption
```

### Commands

Encrypt a new secret:

```bash
sops --encrypt --in-place kubernetes/apps/namespace/app/secret.sops.yaml
```

Edit an encrypted secret:

```bash
sops kubernetes/apps/namespace/app/secret.sops.yaml
# Opens in $EDITOR, auto-encrypts on save
```

Decrypt for reading (don't save):

```bash
sops --decrypt kubernetes/apps/namespace/app/secret.sops.yaml
```

Verify a file is encrypted:

```bash
grep -q "sops:" kubernetes/apps/namespace/app/secret.sops.yaml && echo "Encrypted" || echo "UNENCRYPTED!"
```

### Creating Secrets

All Kubernetes secrets should use the SOPS encrypted format:

```yaml
# secret.sops.yaml
apiVersion: v1
kind: Secret
metadata:
  name: my-secret
  namespace: my-namespace
stringData:
  key: value
```

Then encrypt: `sops --encrypt --in-place secret.sops.yaml`

## Scripts Development Standards

The `scripts/` directory contains utility scripts for local execution.

### Bash Scripts

Requirements:

- Must pass `shellcheck` validation
- Include usage documentation in comments at top of file
- Use proper error handling with `set -euo pipefail`
- Use meaningful exit codes
- Make scripts executable: `chmod +x script.sh`

Example header:

```bash
#!/usr/bin/env bash
# Description: Brief description of what this script does
# Usage: ./script.sh [options]
set -euo pipefail
```

Validation:

```bash
shellcheck scripts/my-script.sh
```

### Python Scripts

Requirements:

- Use `uv` for dependency management
- Use `ruff` for linting and formatting
- Include docstrings and type hints
- Follow PEP 8 style guide

Setup with uv:

```bash
uv venv
source .venv/bin/activate
uv pip install <packages>
```

Linting and formatting:

```bash
ruff check scripts/my-script.py
ruff format scripts/my-script.py
```

Example with type hints:

```python
#!/usr/bin/env python3
"""Brief description of what this script does."""


def main() -> None:
    """Main function."""
    pass


if __name__ == "__main__":
    main()
```

## Testing & Validation

### Flux Health Checks

Check all Flux sources:

```bash
flux get sources git -A
flux get sources oci -A
```

Check Kustomizations:

```bash
flux get ks -A
```

Check Helm Releases:

```bash
flux get hr -A
```

Force reconciliation:

```bash
flux reconcile ks <name> --with-source
flux reconcile hr -n <namespace> <name>
```

### Kubernetes Debugging

Check pod status:

```bash
kubectl get pods -n <namespace>
kubectl get pods -A  # All namespaces
```

Describe resources:

```bash
kubectl describe pod -n <namespace> <pod-name>
kubectl describe helmrelease -n <namespace> <name>
```

View logs:

```bash
kubectl logs -n <namespace> <pod-name>
kubectl logs -n <namespace> <pod-name> -f  # Follow
```

Aggregate logs with stern:

```bash
stern -n <namespace> <app-name>
```

Check events:

```bash
kubectl get events -n <namespace> --sort-by='.metadata.creationTimestamp'
```

### Manifest Validation

Kubeconform validation:

```bash
./scripts/kubeconform.sh
```

Pre-commit hooks:

The repository has pre-commit hooks.
Reference `.taskfiles/repository/taskfile.yaml` to see what runs:

```bash
pre-commit run --all-files
```

## File Naming Conventions

- **SOPS encrypted files**: `*.sops.yaml` (templates without secret values are `*.sops.yaml.tmpl`)
- **Kustomization files**: `kustomization.yaml` or `ks.yaml`
- **HelmRelease files**: `helmrelease.yaml` or `<app>-helmrelease.yaml`
- **App README**: Always `README.md` (not readme.md or README.MD)
- **ConfigMaps/Secrets**: Descriptive names like `app-config.yaml`, `app-secret.sops.yaml`

## Secrets Management Naming Conventions (ESO vs SOPS)

- Prefer Bitwarden/ESO as the primary secrets path; SOPS stays only for minimal bootstrap credentials.
- Bitwarden project: **Homelab**.
  Keep all ExternalSecret targets in this project for consistency and access control.
- Bitwarden item names: `{namespace}-{app}-{purpose}` (e.g., `default-ghost-db`); shared items use `shared-{purpose}`.
- Secret fields: `username`, `password`, `apiKey`, `token`, `certificate`, `privateKey` (avoid generic keys like `value`).
- Kubernetes Secret names mirror Bitwarden items where possible; avoid ambiguous names like `credentials` or `secret`.
- ExternalSecret resource names: `{namespace}-{app}-{source}` (e.g., `default-ghost-bitwarden`).
- ClusterSecretStore name: `bitwarden-cluster-store`; ESO controller ServiceAccount: `external-secrets-controller` in the `external-secrets` namespace.

## Commit Message Convention

All commit messages must follow the [Conventional Commits](https://www.conventionalcommits.org/) specification.

### Format

```text
<type>[optional scope][!]: <description>

[optional body]

[optional footer(s)]
```

### Rules

**Type and Description:**

- Allowed types: `feat`, `fix`, `build`, `chore`, `ci`, `docs`, `style`, `refactor`, `test`, `revert`
- Use imperative, present tense (e.g., "add feature" not "added feature")
- No trailing period on the description
- Prefer lowercase unless referencing a proper noun
- Keep the description concise and specific

**Scope:**

- Use a short, specific scope that identifies the area of change
- Examples: `api`, `ui`, `deps`, `ci`, `docs`, `flux`, `ansible`, `networking`
- Scope is optional but recommended for clarity

**Breaking Changes:**

- Mark breaking changes with `!` after the type/scope: `feat(api)!: change authentication method`
- Include a `BREAKING CHANGE:` footer describing the impact and migration path

**Body:**

- Explain what and why, not how
- Use bullet points for lists
- Avoid repeating the subject line
- Separate from subject with a blank line

**Footers:**

- Use `BREAKING CHANGE:` footer for breaking changes
- Coding assistants MUST indicate their assistance via a co-authored-by message: `Co-authored-by: <agent name><email>`
- Reference issues/PRs: `Closes #123`, `Refs #456`, `Fixes #789`

### Type Guidance

- `feat`: New user-facing behavior or capability
- `fix`: Bug fix that affects users
- `docs`: Documentation only changes
- `style`: Formatting changes that don't affect code meaning (whitespace, formatting, etc.)
- `refactor`: Code changes that neither fix bugs nor add features
- `test`: Adding or updating tests only
- `build`: Changes to build system, dependencies, or tooling (e.g., npm, ansible roles)
- `ci`: CI/CD configuration changes (e.g., GitHub Actions, Flux)
- `chore`: Routine tasks, maintenance, or other changes that don't modify src or test files
- `revert`: Reverts a previous commit

### Examples

```text
feat(networking): add external ingress for blog service

Configures HTTPRoute with external gateway and Cloudflare DNS annotation
to make the blog publicly accessible.

Closes #42
```

```text
fix(cert-manager): resolve certificate renewal failures

The ClusterIssuer was using an expired API token. Updated the secret
with a new token and verified certificate issuance.

Fixes #128
```

```text
chore(deps): update flux to v2.3.0

Updated Flux components to latest stable release for security patches
and performance improvements.
```

```text
feat(storage)!: migrate from openebs-hostpath to rook-ceph

BREAKING CHANGE: All PVCs must be migrated manually. openebs-hostpath storage
class is deprecated and will be removed in the next release.

Migration guide: docs/storage-migration.md

Refs #201
```

## Important Gotchas

### Security

1. **Always verify SOPS files are encrypted before committing**

   ```bash
   # Check all SOPS files are encrypted
   find . -name "*.sops.yaml" -exec grep -L "sops:" {} \;
   # Should return nothing if all are encrypted
   ```

2. **Never commit the age.key file** (it's in .gitignore)

3. **Secrets in Ansible inventory** are also SOPS-encrypted (e.g., `host_vars/*.sops.yaml`)

### DNS & Networking

1. **Split DNS is required** for k8s-gateway to work

- Home DNS server must forward `*.domain.com` to k8s-gateway IP
- Without this, internal services won't resolve

2. **Certificate staging vs production**

- Cluster starts with Let's Encrypt staging certificates
- Switch to production once stable to avoid rate limits
- Staging certs will show browser warnings

3. **Cloudflare tunnel** must be configured for external ingress to work

- Check `kubernetes/apps/network/cloudflared/` for configuration

### Flux & GitOps

1. **Changes may take up to 30 minutes** to reconcile (default interval)

- Force reconciliation for immediate updates

2. **Flux ignores some paths** defined in `kubernetes/flux/config/cluster.yaml`

3. **Bootstrap secrets** must exist in `kubernetes/bootstrap/` before Flux can decrypt other secrets

### Cluster Operations

1. **Don't assume cluster is accessible** - verify connection before running kubectl commands:

   ```bash
   kubectl cluster-info
   ```

2. **Node operations** require Ansible and SSH access to nodes

3. **Rook-Ceph operations** need special care - reference `.taskfiles/rook/taskfile.yaml` before making changes.
   YOU MUST CHECK WITH THE HUMAN BEFORE OPERATING DIRECTLY ON ROOK-CEPH.

### Kubeconfig

- Located at `./kubeconfig` in repository root
- Created by Ansible during k3s installation
- Required for all `kubectl` and `flux` commands
- **Passed via nix develop wrapper**: `nix develop -c env 'KUBECONFIG=./kubeconfig' <command>`

## Ansible Operations

### Inventory Structure

```text
ansible/inventory/
├── hosts.yaml              # Main inventory
├── group_vars/            # Variables for groups
│   ├── all/
│   ├── controller/        # Control plane nodes
│   ├── kubernetes/        # All k8s nodes
│   └── worker/            # Worker nodes
└── host_vars/             # Per-host variables (SOPS-encrypted)
    ├── optiplex0.sops.yaml
    └── ...
```

### Running Playbooks

Check inventory:

```bash
ansible-inventory -i ansible/inventory --list
```

Run a playbook:

```bash
ansible-playbook -i ansible/inventory/hosts.yaml ansible/playbooks/<playbook>.yaml --become
```

### Common Playbooks

- `k3s-install.yaml` - Install k3s on nodes
- `k3s-prepare.yaml` - Prepare nodes for k3s (reboot required)
- `k3s-nuke.yaml` - Completely remove k3s (destructive!)
- `reboot.yaml` - Reboot nodes
- `apt-update.yaml` - Update packages on nodes

## References

- [README.md](./README.md) - Comprehensive setup and user documentation
- [.codex/rules/kubectl.rules](.codex/rules/kubectl.rules) - Security rules for kubectl/flux commands
- [docs/ansible.md](./docs/ansible.md) - Ansible usage details
- [docs/task.md](./docs/task.md) - Task command reference (for humans)
- [Flux Documentation](https://fluxcd.io/flux/) - Flux CD official docs
- [k3s Documentation](https://docs.k3s.io/) - k3s official docs
- [SOPS Documentation](https://github.com/getsops/sops) - SOPS usage and configuration

---

Remember: This repository manages real infrastructure.
Always test changes carefully, verify SOPS encryption, and understand the impact before committing.

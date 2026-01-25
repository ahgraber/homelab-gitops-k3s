{
  description = "A flake to install k8s-homelab environment";

  # Add nixConfig to control what gets used in the flake
  nixConfig = {
    # Only allow these paths to be accessed by the builder
    allowed-uris = [
      "github:NixOS/nixpkgs"
      "github:numtide/devshell"
      "github:numtide/flake-utils"
    ];
    # Exclude everything but the flake.nix file from the build inputs
    flake-registry = "";
  };

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    # nixpkgs-unstable.url = "github:NixOS/nixpkgs/nixos-unstable";
    devshell.url = "github:numtide/devshell";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = {
    self,
    devshell,
    flake-utils,
    nixpkgs,
    # nixpkgs-unstable
  }:
    flake-utils.lib.eachDefaultSystem (system: {
      devShells.default =
        let
          pkgs = import nixpkgs {
            inherit system;
            overlays = [
              devshell.overlays.default
              # # When applied, the unstable nixpkgs set (declared in the flake inputs) will be accessible through 'pkgs.unstable'
              # (final: prev: {
              #   unstable = import nixpkgs-unstable {
              #     system = final.system;
              #     config = { allowUnfree = true; };
              #   };
              # })
              # (final: prev: {
              #   ansible = prev.python311.pkgs.ansible;
              #   ansible-lint = (prev.ansible-lint.override {
              #     python3 = prev.python311;
              #   });
              # })
            ];

            config = {
              allowUnfree = true;
            };
          };
        in
        pkgs.devshell.mkShell {
          name = "k8s-devshell";
          # imports = [];
          # a list of packages to add to the shell environment
          packages = with pkgs; [
            # ansible       # Radically simple IT automation
            # ansible-lint  # Best practices checker for Ansible
            bws # Bitwarden Secrets Manager
            # freelens # Kubernetes IDE
            fluxcd # flux CLI for gitops
            hadolint # Dockerfile Linter JavaScript API
            helmfile # Helmfile is a declarative spec for deploying helm charts
            # kopia          # Cross-platform backup tool
            krew # Package manager for kubectl plugins
            kubectl # Kubernetes CLI
            kubecolor # colorize kubectl output
            kubeconform # FAST Kubernetes manifests validator, with support for Custom Resources
            kubernetes-helm # helm CLI
            kustomize # Customization of kubernetes YAML configurations
            minio-client # CLI for minio, An S3-compatible object storage server
            # nerdctl        # A Docker-compatible CLI for containerd
            openldap # Open source implementation of the Lightweight Directory Access Protocol
            restic # A backup program that is fast, efficient and secure
            # velero         # Kubernetes disaster recovery
            yq-go # Lightweight and portable command-line YAML processor
            #--- containers ---
            docker # Pack, ship and run any application as a lightweight container
            # podman
            colima
            qemu
          ];
          # imports = [ (devshell.importTOML ./devshell.toml) ];
        };
    });
}

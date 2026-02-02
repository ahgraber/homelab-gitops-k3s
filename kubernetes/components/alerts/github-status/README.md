# GitHub Status Alerts (Flux Notification)

This component publishes Flux reconciliation results back to GitHub as commit statuses.
This allows GitHub to display these as commit status checks on the commit being reconciled.

## What it does

- Creates a Flux `Provider` of type `github` pointing at this repo.
- Creates a Flux `Alert` that watches `Kustomization` events (name `*`) in the
  same namespace and sends them to the GitHub provider.
- Because this component is included per-namespace, each namespace gets its own
  `Alert` + `Provider`, and only that namespace's Kustomizations emit statuses.

## Requirements

- A GitHub token with permission to create commit statuses for this repo.

## Files

- `provider.yaml`: GitHub notification provider (repo target + secret ref).
- `alert.yaml`: Watches Kustomization events and forwards them to GitHub.
- `externalsecret.yaml`: TODO placeholder for the token source.

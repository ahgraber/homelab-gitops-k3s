#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Claude Code Hook: Block Kubernetes secret exfiltration and gate cluster mutations.

PreToolUse hook for the Bash tool.

Block mode (exit 2):
  - kubectl get <secret-type> with -o / --output (dumps secret data)
  - Same commands wrapped in `nix <subcmd> ... kubectl`
  - Shell indirection that may bypass direct regex matching

Ask mode (exit 0 + JSON):
  - kubectl mutating verbs (apply, delete, create, replace, exec, cp, etc.)
  - helm install / upgrade / uninstall
  - flux reconcile / suspend / resume / bootstrap / install / uninstall / delete
  - ansible-playbook
  - sops --decrypt / -d
  - All of the above when invoked via `nix <subcmd> ... <tool>`
"""

import json
import re
import sys

# ── Secret-type resources whose raw output must never be dumped ───────────────
_SECRET_RESOURCES = (
    r"secrets?"  # NOQA: S105
    r"|externalsecrets?"
    r"|secretstores?"
    r"|clustersecretstores?"
)

# Matches: kubectl get <secret-resource> [flags] (-o|--output) ...
# Uses -o(?:\s|=|\S) to catch both `-o yaml` and `-ojson` (no space) forms.
_KUBECTL_SECRET_DUMP_RE = re.compile(
    rf"\bkubectl\s+get\s+(?:{_SECRET_RESOURCES})\b"
    r"(?:\s+\S+)*\s+(?:-o(?:\s|=|\S)|--output(?:\s|=))",
    re.IGNORECASE,
)

# Same, but prefixed by `nix <subcmd> [args]` invocation
_NIX_KUBECTL_SECRET_DUMP_RE = re.compile(
    r"\bnix\s+\S+"  # nix run / nix shell / nix develop / ...
    r".*?"
    rf"\bkubectl\s+get\s+(?:{_SECRET_RESOURCES})\b"
    r"(?:\s+\S+)*\s+(?:-o(?:\s|=|\S)|--output(?:\s|=))",
    re.IGNORECASE,
)

# ── Shell indirection that can bypass regex matching (block) ─────────────────
_SHELL_INDIRECTION_RE = re.compile(
    r"\beval\s+"
    r"|\bxargs\s+.*\bkubectl\b"
    r"|\bbash\s+-c\s+"
    r"|\bsh\s+-c\s+"
    r"|\bzsh\s+-c\s+",
    re.IGNORECASE,
)

# ── Cluster-mutating kubectl verbs (ask) ──────────────────────────────────────
_KUBECTL_MUTATE_RE = re.compile(
    r"\bkubectl\s+(?:"
    r"apply"
    r"|create"
    r"|replace"
    r"|delete"
    r"|edit"
    r"|patch"
    r"|rollout\s+restart"
    r"|scale"
    r"|cordon"
    r"|drain"
    r"|uncordon"
    r"|run"
    r"|set\s+\S+"
    r"|label"
    r"|annotate"
    r"|taint"
    r"|expose"
    r"|exec"
    r"|cp"
    r")\b",
    re.IGNORECASE,
)
_NIX_KUBECTL_MUTATE_RE = re.compile(
    r"\bnix\s+\S+.*?"
    r"\bkubectl\s+(?:"
    r"apply|create|replace|delete|edit|patch"
    r"|rollout\s+restart|scale|cordon|drain|uncordon"
    r"|run|set\s+\S+|label|annotate|taint|expose"
    r"|exec|cp"
    r")\b",
    re.IGNORECASE,
)

# ── Helm mutations (ask) ──────────────────────────────────────────────────────
_HELM_MUTATE_RE = re.compile(
    r"\bhelm\s+(?:install|upgrade|uninstall)\b",
    re.IGNORECASE,
)
_NIX_HELM_MUTATE_RE = re.compile(
    r"\bnix\s+\S+.*?\bhelm\s+(?:install|upgrade|uninstall)\b",
    re.IGNORECASE,
)

# ── Flux operations (ask) ─────────────────────────────────────────────────────
_FLUX_MUTATE_RE = re.compile(
    r"\bflux\s+(?:reconcile|suspend|resume|bootstrap|install|uninstall|delete)\b",
    re.IGNORECASE,
)
_NIX_FLUX_MUTATE_RE = re.compile(
    r"\bnix\s+\S+.*?\bflux\s+(?:reconcile|suspend|resume|bootstrap|install|uninstall|delete)\b",
    re.IGNORECASE,
)

# ── Ansible (ask) ─────────────────────────────────────────────────────────────
_ANSIBLE_RE = re.compile(r"\bansible-playbook\b", re.IGNORECASE)

# ── SOPS decrypt (ask) ───────────────────────────────────────────────────────
_SOPS_DECRYPT_RE = re.compile(
    r"\bsops\s+(?:.*\s)?(?:--decrypt|-d)\b",
    re.IGNORECASE,
)


# ── Hook output helpers ───────────────────────────────────────────────────────
def block(message: str) -> None:
    """Write message to stderr and exit with code 2 to block the tool call."""
    sys.stderr.write(message + "\n")
    sys.exit(2)


def ask(reason: str) -> None:
    """Emit a permissionDecision=ask JSON response and exit with code 0."""
    sys.stdout.write(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "ask",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    sys.exit(0)


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    """Parse hook input and enforce secret/mutation guards."""
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(2)  # fail-closed: this hook is Bash-only (sensitive tool)

    if data.get("tool_name") != "Bash":
        sys.exit(0)

    command: str = data.get("tool_input", {}).get("command", "")
    if not command:
        sys.exit(0)

    # ── Block: secret exfiltration ────────────────────────────────────────────
    if _KUBECTL_SECRET_DUMP_RE.search(command) or _NIX_KUBECTL_SECRET_DUMP_RE.search(command):
        block(
            "Blocked: kubectl get <secret-resource> with -o / --output.\n"
            "Dumping secret resources in machine-readable format exfiltrates "
            "plaintext credentials, TLS private keys, or service-account tokens "
            "into Claude's context. Use `kubectl describe secret <name>` to "
            "inspect metadata without exposing values."
        )

    # ── Block: shell indirection that may bypass regex guards ─────────────────
    if _SHELL_INDIRECTION_RE.search(command):
        block(
            "Blocked: shell indirection detected (eval, bash -c, sh -c, "
            "xargs kubectl, or similar). These patterns can bypass safety "
            "guards. Run the underlying command directly instead."
        )

    # ── Ask: cluster-mutating kubectl verbs ───────────────────────────────────
    if _KUBECTL_MUTATE_RE.search(command) or _NIX_KUBECTL_MUTATE_RE.search(command):
        ask(
            "This command mutates live Kubernetes cluster state "
            f"(`{command[:120]}`). Confirm this targets the intended cluster "
            "and namespace before proceeding."
        )

    # ── Ask: Helm mutations ───────────────────────────────────────────────────
    if _HELM_MUTATE_RE.search(command) or _NIX_HELM_MUTATE_RE.search(command):
        ask(
            "This Helm command installs, upgrades, or removes a release on a "
            f"live cluster (`{command[:120]}`). Confirm the release name, "
            "namespace, and chart version before proceeding."
        )

    # ── Ask: Flux operations ──────────────────────────────────────────────────
    if _FLUX_MUTATE_RE.search(command) or _NIX_FLUX_MUTATE_RE.search(command):
        ask(
            "This Flux command triggers a reconciliation, suspension, or "
            f"resumption on a live cluster (`{command[:120]}`). Confirm the "
            "target resource and namespace before proceeding."
        )

    # ── Ask: Ansible ──────────────────────────────────────────────────────────
    if _ANSIBLE_RE.search(command):
        ask(
            "This ansible-playbook command will execute tasks against one or "
            f"more hosts (`{command[:120]}`). Confirm the inventory target and "
            "playbook contents before proceeding."
        )

    # ── Ask: SOPS decrypt ────────────────────────────────────────────────────
    if _SOPS_DECRYPT_RE.search(command):
        ask(
            "This sops command decrypts secret data which would expose "
            f"plaintext values (`{command[:120]}`). Confirm this is intentional "
            "before proceeding."
        )

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(2)  # fail-closed: Bash is a sensitive tool

#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Claude Code Hook: Block Kubernetes operations requiring confirmation.

PreToolUse hook for the Bash tool.
Loads homelab-specific rules from block-k8s-ops-patterns.toml and matches each
command against them, producing a hard block (exit 2) or a confirmation prompt
(exit 0 + JSON) as specified by the matched rule's mode.

Block mode (exit 2):
  - kubectl get <secret-type> with -o / --output (dumps secret data)
  - Shell indirection that may bypass kubectl regex guards (xargs kubectl)

Ask mode (exit 0 + JSON):
  - kubectl mutating verbs (apply, delete, create, replace, exec, cp, etc.)
  - flux reconcile / suspend / resume / bootstrap / install / uninstall / delete
  - ansible-playbook
  - sops --decrypt / -d

If the pattern file is missing or unreadable, the hook exits 0 (fail-open on
own configuration errors rather than blocking all Bash commands).
"""

import json
from pathlib import Path
import re
import sys
import tomllib


def load_rules() -> list[dict]:
    """Load rules from the co-located TOML file. Return [] on any error.

    Supports both flat (``[[rules]]``) and nested (``[[category.rules]]``)
    TOML structures. Nested categories are flattened into a single list.
    """
    patterns_file = Path(__file__).parent / "block-k8s-ops-patterns.toml"
    try:
        with open(patterns_file, "rb") as f:
            data = tomllib.load(f)
    except Exception:
        return []

    # Flat structure: [[rules]]
    if "rules" in data and isinstance(data["rules"], list):
        return data["rules"]

    # Nested structure: [[category.rules]]
    all_rules: list[dict] = []
    for _, section in data.items():
        if isinstance(section, dict) and "rules" in section:
            all_rules.extend(section["rules"])
    return all_rules


_AI_INSTRUCTIONS = """
---
AI INSTRUCTIONS:
You have been blocked from performing this operation. Do NOT attempt to find alternative commands, equivalent steps, or workarounds that achieve the same result through a different path.

Stop and report the following to the user immediately:
1. Your current task — what you were working on
2. Your intended step — what you were trying to do and why
3. What was blocked — the specific action blocked and the reason given above
4. How the user can help — describe exactly what command or steps the user could run manually to complete this on your behalf, and explain why they might or might not want to proceed"""


def make_ask_json(reason: str) -> str:
    """Build the permissionDecision=ask JSON response for stdout."""
    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": reason,
            }
        }
    )


def main() -> None:
    """Parse hook input and enforce k8s secret/mutation guards."""
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(2)  # fail-closed: this hook only handles Bash (sensitive tool)

    if data.get("tool_name") != "Bash":
        sys.exit(0)

    command = data.get("tool_input", {}).get("command", "")
    if not command:
        sys.exit(0)

    rules = load_rules()
    if not rules:
        sys.exit(0)

    for rule in rules:
        pattern = rule.get("pattern", "")
        if not pattern:
            continue

        flags = re.IGNORECASE if rule.get("case_insensitive", False) else 0
        try:
            compiled = re.compile(pattern, flags)
        except re.error:
            continue

        if not compiled.search(command):
            continue

        description = rule.get("description", "")
        reason = rule.get("reason", "")
        mode = rule.get("mode", "block")

        explanation = description
        if reason:
            explanation += f"\n\n{reason}"

        if mode == "block":
            sys.stderr.write(f"Blocked: {explanation}\n{_AI_INSTRUCTIONS}\n")
            sys.exit(2)
        elif mode == "ask":
            sys.stdout.write(make_ask_json(explanation))
            sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        # ErrorHandlingByDamagePotential: this hook only handles Bash
        # (a sensitive tool), so always fail-closed on internal error.
        sys.exit(2)

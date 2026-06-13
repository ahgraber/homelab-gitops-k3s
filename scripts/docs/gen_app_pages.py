#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Aggregate per-app README.md files into Quarto pages for the Great Docs site.

Crawls ``kubernetes/apps/<namespace>/<app>/README.md`` (and nested component
READMEs), copies+transforms each into ``docs/projects/<namespace>/<app>.qmd``,
and runs a secret/leak scan on the way through. Because the resulting site is
published to **public** GitHub Pages, the scan is a build gate: a hard hit
fails the build; a soft hit warns but continues.

The canonical README stays in the app directory (single source of truth); the
``docs/projects/`` tree is generated output and is gitignored.

Usage:
    uv run scripts/docs/gen_app_pages.py            # generate (warns on soft hits)
    uv run scripts/docs/gen_app_pages.py --strict   # fail on soft hits too
    uv run scripts/docs/gen_app_pages.py --check     # scan only, write nothing
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

# --- configuration ----------------------------------------------------------

APPS_DIR = Path("kubernetes/apps")
OUTPUT_DIR = Path("docs/projects")
GITHUB_BLOB = "https://github.com/ahgraber/homelab-gitops-k3s/blob/main"

# Curation: namespaces and path fragments to exclude from the published site.
EXCLUDE_NAMESPACES = {"debug"}
EXCLUDE_PATH_FRAGMENTS = {"/app/icons/"}  # non-app READMEs (e.g. homepage icons)

# --- secret / leak scanning -------------------------------------------------

# Hard hits: near-certain credential material. Any hit fails the build.
HARD_PATTERNS: dict[str, re.Pattern[str]] = {
    "age-secret-key": re.compile(r"AGE-SECRET-KEY-1[0-9A-Z]+"),
    "private-key-block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----"),
    "aws-access-key": re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    "github-pat": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "slack-token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
}

# Soft hits: often fine (placeholders, examples) but worth a human glance.
SOFT_PATTERNS: dict[str, re.Pattern[str]] = {
    "private-ip": re.compile(r"\b(?:10\.\d{1,3}|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b"),
    "op-reference": re.compile(r"op://[\w.-]+/[\w.-]+"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "bearer-or-secret-literal": re.compile(r"(?i)\b(?:bearer\s+[A-Za-z0-9._-]{12,}|(?:password|secret|token|apikey)\s*[:=]\s*[\"']?[A-Za-z0-9._/+-]{12,})"),
}

# Lines that are obviously templated/example are exempt from soft warnings.
PLACEHOLDER_HINT = re.compile(r"<[\w-]+>|\$\{|example\.com|EXAMPLE|changeme|<domain>|placeholder", re.IGNORECASE)


@dataclass
class Finding:
    path: Path
    line_no: int
    rule: str
    severity: str  # "hard" | "soft"
    snippet: str


@dataclass
class Result:
    written: list[Path] = field(default_factory=list)
    skipped: list[tuple[Path, str]] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)


def scan(path: Path, text: str) -> list[Finding]:
    """Scan README text for credential material and risky literals."""
    out: list[Finding] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for rule, pat in HARD_PATTERNS.items():
            if pat.search(line):
                out.append(Finding(path, line_no, rule, "hard", line.strip()[:120]))
        if PLACEHOLDER_HINT.search(line):
            continue  # templated/example line — skip soft rules
        for rule, pat in SOFT_PATTERNS.items():
            if pat.search(line):
                out.append(Finding(path, line_no, rule, "soft", line.strip()[:120]))
    return out


# --- transformation ---------------------------------------------------------

H1 = re.compile(r"^#\s+(.*)$", re.MULTILINE)
MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")


def derive_title(text: str, fallback: str) -> str:
    """Pull a display title from the first H1, stripping any markdown link."""
    m = H1.search(text)
    if not m:
        return fallback
    title = m.group(1).strip()
    # `# [Actual Budget](https://...)` -> `Actual Budget`
    link = MD_LINK.fullmatch(title)
    return link.group(1) if link else title


def namespace_of(readme: Path) -> str:
    parts = readme.relative_to(APPS_DIR).parts
    return parts[0] if parts else "uncategorized"


def output_path(readme: Path) -> Path:
    """docs/projects/<namespace>/<app[-subcomponent]>.qmd"""
    rel = readme.parent.relative_to(APPS_DIR)
    ns, *rest = rel.parts
    slug = "-".join(rest) if rest else ns
    return OUTPUT_DIR / ns / f"{slug}.qmd"


def transform(readme: Path, text: str) -> str:
    """Wrap a README in QMD frontmatter and append a source link."""
    title = derive_title(text, readme.parent.name)
    src = f"{GITHUB_BLOB}/{readme.as_posix()}"
    # Drop the first H1 — the title goes in frontmatter to avoid duplication.
    body = H1.sub("", text, count=1).lstrip("\n")
    front = f'---\ntitle: "{title}"\n---\n\n'
    footer = f'\n\n::: {{.callout-note appearance="minimal"}}\nSource: [`{readme.as_posix()}`]({src})\n:::\n'
    return front + body + footer


def is_excluded(readme: Path) -> str | None:
    # The apps-root README (kubernetes/apps/README.md) is not an app.
    if readme.parent.relative_to(APPS_DIR).parts == ():
        return "apps-root README (not an app)"
    ns = namespace_of(readme)
    if ns in EXCLUDE_NAMESPACES:
        return f"excluded namespace '{ns}'"
    posix = "/" + readme.as_posix()
    for frag in EXCLUDE_PATH_FRAGMENTS:
        if frag in posix:
            return f"excluded path fragment '{frag.strip('/')}'"
    return None


def generate(root: Path, *, write: bool) -> Result:
    res = Result()
    apps = (root / APPS_DIR)
    if not apps.is_dir():
        sys.exit(f"error: {apps} not found — run from the repo root")

    if write and (root / OUTPUT_DIR).exists():
        shutil.rmtree(root / OUTPUT_DIR)

    for readme in sorted(apps.rglob("README.md")):
        rel_readme = readme.relative_to(root)
        reason = is_excluded(rel_readme)
        if reason:
            res.skipped.append((rel_readme, reason))
            continue

        text = readme.read_text(encoding="utf-8")
        res.findings.extend(scan(rel_readme, text))

        if write:
            dest = root / output_path(rel_readme)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(transform(rel_readme, text), encoding="utf-8")
            res.written.append(dest.relative_to(root))

    return res


# --- reporting --------------------------------------------------------------

def report(res: Result, *, strict: bool) -> int:
    hard = [f for f in res.findings if f.severity == "hard"]
    soft = [f for f in res.findings if f.severity == "soft"]

    print(f"apps: {len(res.written)} written, {len(res.skipped)} skipped")
    if res.skipped:
        print("\nskipped:")
        for path, reason in res.skipped:
            print(f"  - {path}  ({reason})")

    def dump(label: str, items: list[Finding]) -> None:
        print(f"\n{label}: {len(items)}")
        for f in items:
            print(f"  {f.path}:{f.line_no}  [{f.rule}]  {f.snippet}")

    if soft:
        dump("SOFT findings (review)", soft)
    if hard:
        dump("HARD findings (block)", hard)

    if hard:
        print("\nBUILD BLOCKED: hard secret findings present.")
        return 1
    if soft and strict:
        print("\nBUILD BLOCKED: soft findings present and --strict set.")
        return 1
    print("\nOK")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=Path.cwd(), help="repo root (default: cwd)")
    ap.add_argument("--strict", action="store_true", help="treat soft findings as build failures")
    ap.add_argument("--check", action="store_true", help="scan only; do not write pages")
    args = ap.parse_args()

    res = generate(args.root.resolve(), write=not args.check)
    sys.exit(report(res, strict=args.strict))


if __name__ == "__main__":
    main()

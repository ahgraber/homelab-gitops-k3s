#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11,<3.13"
# dependencies = [
#   "beautifulsoup4>=4.13",
#   "pyyaml>=6.0",
# ]
# ///
"""Detect rendering regressions between two versions of markdown files.

Formatter and linter passes (`mdformat`, `rumdl`) rewrap prose and normalize
markers.  Those edits are supposed to be render-neutral, but reflow can split an
inline construct across lines and silently change what a reader sees -- a link
whose `[text](url)` straddles a newline stops being a link, an emphasis run that
is closed and reopened gains stray spaces, and a moved sentence changes meaning.

Each version is rendered with pandoc and compared on four projections:

- **document** -- the rendered HTML, with whitespace collapsed inside text nodes
  so rewrapping is invisible, but with element boundaries and code-block
  interiors left intact.  Catches content loss, reordering, blocks splitting or
  merging, table cells collapsing, and reformatted code.
- **links** -- the `href`/`src` multiset; catches links that stopped parsing.
- **targets** -- whether each relative link still resolves to a file on disk and,
  for `#fragment` links, to a heading in the target document.
- **frontmatter** -- the parsed YAML block, which pandoc discards as metadata and
  which no other projection can see.

Requires `pandoc` on PATH, and a hook runner for `--run-hooks`; `--doctor`
reports which of those are missing.

Usage::

    # Compare the working tree against HEAD (default)
    ./scripts/check_markdown_render.py

    # Compare a formatting commit against its parent
    ./scripts/check_markdown_render.py --base HEAD~1 --head HEAD

    # Run the repo's own hooks on a throwaway copy of the tree and check what
    # they would do.  This is the check to run after editing hook config: it
    # isolates the hooks from any edits of your own, and what runs is whatever
    # .pre-commit-config.yaml says, at the pinned revisions CI uses.
    ./scripts/check_markdown_render.py --run-hooks

    # Narrow to the hooks you are actually changing
    ./scripts/check_markdown_render.py --hook mdformat --hook rumdl-fmt

    # Limit to specific paths
    ./scripts/check_markdown_render.py skills/commit-message

Exits non-zero when any file renders differently.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, field
import difflib
import hashlib
import logging
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from textwrap import indent
import yaml

from bs4 import BeautifulSoup, NavigableString, Tag

logger = logging.getLogger(__name__)

WHITESPACE = re.compile(r"\s+")
FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---[ \t]*\r?\n", re.DOTALL)
URL_SCHEME = re.compile(r"\A[a-zA-Z][a-zA-Z0-9+.-]*:|\A//")

# Hook runners understood by --run-hooks, in preference order.  Both read the
# same config and take the same `run <id> --files` arguments, so which one drives
# the mirror only affects speed.
RUNNERS = ["prek", "pre-commit"]
HOOK_CONFIG = ".pre-commit-config.yaml"

# Elements that own a line in the serialized document.  An element holding any
# of these is emitted as an open/close pair with its children indented beneath;
# anything else is emitted inline, so rewrapped prose collapses to one line.
BLOCK_TAGS = frozenset({
    "address", "article", "aside", "blockquote", "caption", "colgroup", "dd", "details", "div", "dl", "dt",
    "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr",
    "li", "main", "nav", "ol", "p", "pre", "section", "summary", "table", "tbody", "td", "tfoot", "th",
    "thead", "tr", "ul",
})  # fmt: skip

# Attributes that change what a reader sees or where a link goes.  `class` is
# excluded because pandoc's own bookkeeping churns it; a code block's language is
# recovered from it separately, by `code_language`.
# `style` carries table-cell alignment and, on raw HTML the formatters pass
# through untouched, whether a block is displayed at all; `open`/`hidden` decide
# whether a disclosure's contents are painted.  None of them affect the text.
SIGNIFICANT_ATTRS = [
    "href", "src", "alt", "title", "id", "start", "reversed", "align", "colspan", "rowspan", "type",
    "style", "open", "hidden", "checked", "disabled",
]  # fmt: skip

# Info strings that all mean "no language".  Formatters routinely spell an
# unlabelled fence `text`, which is not a change worth reporting -- but a fence
# going from a real language to `text` is, and no content-based projection would
# see it, because the code inside is untouched.
PLAIN_LANGUAGES = frozenset({"", "plain", "plaintext", "text", "txt"})

# Inline elements whose leading/trailing whitespace is hoisted out before
# comparison, so an emphasis run closing before a space instead of after it is
# not reported.  `code` is excluded: spacing inside a code span is visible.
HOISTABLE_INLINE = frozenset({"a", "del", "em", "strong", "sub", "sup"})

# Lines of context shown on either side of a hunk in the document diff.
DIFF_CONTEXT = 2


@dataclass
class Render:
    """The comparable projections of one rendered markdown file."""

    document: list[str]
    links: Counter[str]
    targets: dict[str, bool]
    frontmatter: object
    error: str = ""


@dataclass
class Finding:
    """Differences detected for a single file."""

    path: str
    document_diff: list[str] = field(default_factory=list)
    links_lost: list[str] = field(default_factory=list)
    links_gained: list[str] = field(default_factory=list)
    targets_broken: list[str] = field(default_factory=list)
    frontmatter_diff: list[str] = field(default_factory=list)
    unrenderable: str = ""

    def __bool__(self) -> bool:
        """Return True when the file rendered differently, or could not be checked at all."""
        return bool(
            self.document_diff
            or self.links_lost
            or self.links_gained
            or self.targets_broken
            or self.frontmatter_diff
            or self.unrenderable
        )


def git(*args: str) -> subprocess.CompletedProcess[str]:
    """Run a git command and capture its output."""
    return subprocess.run(  # noqa: S603
        ["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False
    )


def repo_root() -> Path:
    """Return the top level of the current git repository."""
    result = git("rev-parse", "--show-toplevel")
    if result.returncode != 0:
        logger.error("not inside a git repository")
        sys.exit(2)
    return Path(result.stdout.strip())


def changed_files(base: str, head: str | None, paths: list[str]) -> list[str]:
    """List markdown files that differ between `base` and `head` (or the working tree)."""
    args = ["diff", "--name-only", "-z", base]
    if head:
        args.append(head)
    # Pathspecs narrow the scan; the `.md` filter below keeps the result markdown-only.
    args += ["--", *paths] if paths else ["--", "*.md"]

    result = git(*args)
    if result.returncode != 0:
        logger.error("git diff failed: %s", result.stderr.strip())
        sys.exit(2)

    # -z separates paths with NUL, so paths containing spaces survive intact.
    return sorted(p for p in result.stdout.split("\0") if p.endswith(".md"))


def tracked_files(paths: list[str]) -> list[str]:
    """List every tracked markdown file, optionally narrowed by pathspec."""
    result = git("ls-files", "-z", "--", *(paths or ["*.md"]))
    if result.returncode != 0:
        logger.error("git ls-files failed: %s", result.stderr.strip())
        sys.exit(2)
    return sorted(p for p in result.stdout.split("\0") if p.endswith(".md"))


def read_version(path: str, rev: str | None, root: Path) -> str | None:
    """Read a file at a git revision, or from the working tree when `rev` is None."""
    if rev is None:
        file = root / path
        return file.read_text(encoding="utf-8") if file.is_file() else None

    result = git("show", f"{rev}:{path}")
    return result.stdout if result.returncode == 0 else None


class PandocError(RuntimeError):
    """Raised when pandoc cannot render a document at all."""


def to_html(markdown: str) -> str:
    """Render markdown to HTML with pandoc.

    `--no-highlight` suppresses the per-line `<a href="#cb1-1">` anchors pandoc's
    syntax highlighter injects, which would otherwise dominate the link inventory
    whenever a code block changes length.
    """
    result = subprocess.run(
        ["pandoc", "--from", "gfm", "--to", "html", "--no-highlight"],
        input=markdown,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode != 0:
        # A document pandoc refuses is the strongest finding there is -- most
        # often a formatter has mangled the YAML frontmatter -- so this is
        # reported as a difference rather than killing the run.
        raise PandocError(collapse(result.stderr or "").strip())
    return result.stdout


def collapse(text: str) -> str:
    """Collapse runs of whitespace to a single space."""
    return WHITESPACE.sub(" ", text)


def hoist_inline_whitespace(soup: BeautifulSoup) -> None:
    """Move leading and trailing spaces out of inline elements.

    `foo <em>bar</em>` and `foo<em> bar</em>` render identically, and formatters
    move emphasis boundaries across adjacent spaces routinely.  Normalizing where
    the space sits keeps that churn out of the diff, while a space that was added
    or removed outright still shows up.
    """
    for element in soup.find_all(list(HOISTABLE_INLINE)):
        if element.find_parent("pre"):
            continue
        # Each edge is re-read after the other is rewritten: on a single-child
        # element the two edges are the same node, and replacing it detaches the
        # reference the second pass would otherwise mutate.
        for edge, side, strip, place in (
            (0, slice(None, 1), str.lstrip, "insert_before"),
            (-1, slice(-1, None), str.rstrip, "insert_after"),
        ):
            children = list(element.children)
            if not children:
                break
            node = children[edge]
            if isinstance(node, NavigableString) and str(node)[side].isspace():
                node.replace_with(NavigableString(strip(str(node))))
                getattr(element, place)(NavigableString(" "))


def attrs_of(element: Tag) -> str:
    """Render the attributes that affect what a reader sees, in a stable order."""
    pairs = [(name, element.get(name)) for name in SIGNIFICANT_ATTRS if element.get(name) is not None]
    return "".join(f' {name}="{" ".join(v) if isinstance(v, list) else v}"' for name, v in pairs)


def code_language(pre: Tag) -> str:
    """Return a code block's fence info string, normalized so 'no language' has one spelling."""
    classes = pre.get("class") or []
    code = pre.find("code")
    if not classes and code is not None:
        classes = code.get("class") or []
    language = " ".join(classes).strip()
    return "" if language.lower() in PLAIN_LANGUAGES else language


def serialize(node: Tag, depth: int, out: list[str]) -> None:
    """Emit one line per block element, with inline content collapsed onto it."""
    for child in node.children:
        if isinstance(child, NavigableString):
            text = collapse(str(child)).strip()
            if text:
                out.append("  " * depth + text)
            continue
        if not isinstance(child, Tag):
            continue

        if child.name == "pre":
            # Indentation and blank lines inside a code block are content, so the
            # interior is compared verbatim rather than collapsed.  A trailing
            # newline is kept too: dropping it removes a visible blank line.
            language = code_language(child)
            # Built separately: nesting this f-string inside the next one would
            # reuse the outer quote, which is a syntax error before Python 3.12.
            label = f' lang="{language}"' if language else ""
            out.append("  " * depth + f"<pre{label}{attrs_of(child)}>")
            out += ["  " * (depth + 1) + "|" + line for line in child.get_text().split("\n")]
            out.append("  " * depth + "</pre>")
            continue

        if any(isinstance(c, Tag) and c.name in BLOCK_TAGS for c in child.children):
            out.append("  " * depth + f"<{child.name}{attrs_of(child)}>")
            serialize(child, depth + 1, out)
            out.append("  " * depth + f"</{child.name}>")
        else:
            out.append("  " * depth + f"<{child.name}{attrs_of(child)}>{collapse(child.decode_contents()).strip()}")


def parse_frontmatter(markdown: str) -> object:
    """Return the parsed YAML frontmatter, a marker if it is unparsable, or None."""
    match = FRONTMATTER.match(markdown)
    if not match:
        return None
    try:
        return yaml.safe_load(match.group(1))
    except yaml.YAMLError as err:
        return f"<unparsable: {err}>"


def link_targets(links: list[str], path: str, root: Path, ids: set[str]) -> dict[str, bool]:
    """Resolve each repo-relative link, reporting whether it still points at something."""
    resolved: dict[str, bool] = {}
    for link in links:
        if not link or URL_SCHEME.match(link) or link.startswith(("mailto:", "tel:")):
            continue
        target, _, fragment = link.partition("#")
        if not target:
            # An in-document anchor; pandoc derives heading ids from heading text.
            resolved[link] = fragment in ids
            continue
        file = (root / path).parent / target
        if not file.exists():
            resolved[link] = False
        elif fragment and file.suffix == ".md":
            resolved[link] = fragment in heading_ids(file)
        else:
            resolved[link] = True
    return resolved


def heading_ids(file: Path) -> set[str]:
    """Return the anchor ids pandoc derives for a markdown file's headings."""
    try:
        html = to_html(file.read_text(encoding="utf-8"))
    except (OSError, PandocError):
        # An unreadable target cannot confirm the anchor either way; treat it as
        # present so a separate problem is not reported as a broken link here.
        return set()
    return {tag["id"] for tag in BeautifulSoup(html, "html.parser").find_all(id=True)}


def render(markdown: str, path: str, root: Path) -> Render:
    """Render markdown and extract its comparable projections."""
    try:
        html = to_html(markdown)
    except PandocError as err:
        return Render(
            document=[f"<pandoc refused this document: {err}>"],
            links=Counter(),
            targets={},
            frontmatter=parse_frontmatter(markdown),
            error=str(err),
        )

    soup = BeautifulSoup(html, "html.parser")
    hoist_inline_whitespace(soup)

    links = [str(tag.get("href") or tag.get("src") or "") for tag in soup.find_all(["a", "img"])]
    ids = {tag["id"] for tag in soup.find_all(id=True)}

    document: list[str] = []
    serialize(soup, 0, document)

    return Render(
        document=document,
        links=Counter(links),
        targets=link_targets(links, path, root, ids),
        frontmatter=parse_frontmatter(markdown),
    )


def counter_delta(before: Counter[str], after: Counter[str]) -> tuple[list[str], list[str]]:
    """Return what the multiset lost and gained, so duplicate counts are not masked."""
    lost = sorted((before - after).elements())
    gained = sorted((after - before).elements())
    return lost, gained


def compare_renders(path: str, old: Render, new: Render) -> Finding:
    """Diff two renders of the same file across every projection."""
    finding = Finding(path=path)

    # A file pandoc refuses on both sides diffs to nothing, which would read as a
    # clean bill of health for a file that was never actually checked.
    if old.error and new.error:
        finding.unrenderable = new.error

    if old.document != new.document:
        finding.document_diff = [
            line
            for line in difflib.unified_diff(
                old.document, new.document, "before", "after", n=DIFF_CONTEXT, lineterm=""
            )
            if not line.startswith(("---", "+++"))
        ]
    finding.links_lost, finding.links_gained = counter_delta(old.links, new.links)
    # Compared as sets of broken links rather than per-link, so retargeting a
    # working link at a missing file counts even though the href itself changed.
    # Links already broken before the change are somebody else's problem.
    broken_before = {link for link, ok in old.targets.items() if not ok}
    finding.targets_broken = sorted({link for link, ok in new.targets.items() if not ok} - broken_before)
    if old.frontmatter != new.frontmatter:
        finding.frontmatter_diff = list(
            difflib.unified_diff(
                yaml.safe_dump(old.frontmatter, sort_keys=True).splitlines(),
                yaml.safe_dump(new.frontmatter, sort_keys=True).splitlines(),
                lineterm="",
                n=1,
            )
        )[2:]
    return finding


def compare_revisions(path: str, base: str, head: str | None, root: Path) -> Finding | None:
    """Compare one file's rendering across the two revisions."""
    before = read_version(path, base, root)
    after = read_version(path, head, root)
    if before is None or after is None:
        # Added or deleted outright; there is no prior rendering to regress from.
        logger.debug("skipping %s (added or deleted)", path)
        return None
    if before == after:
        return None
    return compare_renders(path, render(before, path, root), render(after, path, root)) or None


def resolve_runner(requested: str | None, root: Path) -> str:
    """Return the hook runner to drive, preferring an explicit choice."""
    if not (root / HOOK_CONFIG).is_file():
        logger.error("no %s at the repository root, so there are no hooks to run", HOOK_CONFIG)
        sys.exit(2)
    candidates = [requested] if requested else RUNNERS
    for name in candidates:
        if shutil.which(name):
            return name
    logger.error("no hook runner on PATH (looked for %s)", ", ".join(candidates))
    sys.exit(2)


def mirror_tree(root: Path, workdir: Path) -> None:
    """Copy every tracked file into `workdir` and stage it as a git repository.

    The whole tree is mirrored rather than a curated list of config files:
    hooks read their configuration from wherever they please -- the repo root, a
    nested directory, a key in `pyproject.toml` -- and one that quietly falls
    back to its defaults would make the comparison prove nothing.  Contents come
    from the working tree, so config you are still editing is what gets tested.

    The mirror is a git repository because that is what the runner requires, and
    everything is staged so its stash of unstaged changes has nothing to do.
    """
    result = git("ls-files", "-z")
    if result.returncode != 0:
        logger.error("git ls-files failed: %s", result.stderr.strip())
        sys.exit(2)

    for path in (p for p in result.stdout.split("\0") if p):
        source = root / path
        # A tracked file can be absent from the working tree: deleted but not yet
        # committed, or the placeholder directory of an uninitialized submodule.
        if not source.is_file():
            continue
        destination = workdir / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    for args in (("init", "-q"), ("add", "-A")):
        staged = subprocess.run(["git", "-C", str(workdir), *args], capture_output=True, text=True, check=False)  # noqa: S603
        if staged.returncode != 0:
            logger.error("git %s failed in the mirror: %s", args[0], staged.stderr.strip())
            sys.exit(2)


def corpus_digest(files: list[str], workdir: Path) -> dict[str, str]:
    """Hash each mirrored file, so what a hook rewrote can be attributed to it."""
    return {
        path: hashlib.sha256((workdir / path).read_bytes()).hexdigest() if (workdir / path).is_file() else ""
        for path in files
    }


def run_hooks(runner: str, hooks: list[str], files: list[str], workdir: Path) -> None:
    """Run the repo's hooks over the mirrored corpus, in the order given."""
    for hook in hooks or [""]:
        label = hook or "every applicable hook"
        before = corpus_digest(files, workdir)
        # The hook id is positional and has to precede `--files`, whose trailing
        # list would otherwise swallow it as a path and run every hook instead.
        argv = [runner, "run", *([hook] if hook else []), "--color=never", "--files", *files]
        result = subprocess.run(argv, cwd=workdir, capture_output=True, text=True, check=False)  # noqa: S603
        output = (result.stdout + result.stderr).strip()
        logger.debug("%s\n%s", shlex.join(argv), output)

        changed = [path for path, digest in corpus_digest(files, workdir).items() if before[path] != digest]
        logger.info("%s rewrote %d file(s)", label, len(changed))
        if result.returncode != 0 and not changed:
            # A nonzero exit is the normal outcome of a hook that rewrote
            # something -- both runners report that as a failure -- so only a
            # nonzero run that changed nothing means the hook is itself broken.
            logger.warning("%s exited %d and rewrote nothing:\n%s", label, result.returncode, indent(output, "    "))


def compare_hooked(files: list[str], runner: str, hooks: list[str], root: Path) -> list[Finding]:
    """Render each file, run the repo's hooks on a throwaway copy, and render again."""
    with tempfile.TemporaryDirectory(prefix="check-markdown-render-") as tmp:
        workdir = Path(tmp)
        mirror_tree(root, workdir)

        corpus = [path for path in files if (workdir / path).is_file()]
        for path in sorted(set(files) - set(corpus)):
            logger.debug("skipping %s (tracked but not in the working tree)", path)
        run_hooks(runner, hooks, corpus, workdir)

        findings = []
        rewritten = 0
        for path in corpus:
            before = (root / path).read_text(encoding="utf-8")
            mirrored = workdir / path
            if not mirrored.is_file():
                findings.append(Finding(path=path, unrenderable="the hook run removed this file"))
                continue
            after = mirrored.read_text(encoding="utf-8")
            if before == after:
                continue
            rewritten += 1
            # Renders resolve link targets against the real tree, not the mirror,
            # so a file the corpus filter excluded still counts as present.
            if finding := compare_renders(path, render(before, path, root), render(after, path, root)):
                findings.append(finding)

        # Rewriting nothing is the expected result on an already-formatted tree,
        # so it is reported without alarm; a hook that failed to run at all is
        # caught by `run_hooks`, which knows the difference.
        logger.info("hooks rewrote %d of %d file(s)", rewritten, len(corpus))
        return findings


def report(findings: list[Finding], total: int) -> None:
    """Print findings to stdout, grouped by the kind of regression.

    The report is what the run is for, so it goes to stdout and stays pageable
    and redirectable; the log keeps stderr for diagnostics about the run itself.
    """
    print(f"compared {total} markdown file(s)")
    if not findings:
        print("no rendering differences found")
        return

    sections = [
        ("COULD NOT BE CHECKED", lambda f: f.unrenderable, lambda f: [f.unrenderable]),
        ("FRONTMATTER CHANGED", lambda f: f.frontmatter_diff, lambda f: f.frontmatter_diff),
        ("LINK TARGETS BROKEN", lambda f: f.targets_broken, lambda f: [f"broken {t}" for t in f.targets_broken]),
        (
            "LINKS CHANGED",
            lambda f: f.links_lost or f.links_gained,
            lambda f: [f"lost   {x}" for x in f.links_lost] + [f"gained {x}" for x in f.links_gained],
        ),
        ("DOCUMENT CHANGED", lambda f: f.document_diff, lambda f: f.document_diff),
    ]

    for title, selector, lines in sections:
        matched = [f for f in findings if selector(f)]
        if not matched:
            continue
        print(f"\n=== {title} ({len(matched)} file(s)) ===")
        for finding in matched:
            print(finding.path)
            for line in lines(finding):
                print(f"    {line}")


def doctor() -> int:
    """Report whether each of the script's dependencies is present.

    The script is meant to be vendored into projects that may have none of them,
    so the failure mode worth avoiding is a run that exits with one terse error
    at a time.  This names everything at once, and what each thing is needed for.
    """
    found = git("rev-parse", "--show-toplevel")
    root = Path(found.stdout.strip()) if found.returncode == 0 else None
    checks = [
        ("pandoc", shutil.which("pandoc") or "", "required -- every comparison renders through it"),
        ("git repository", str(root) if root else "", "required -- the corpus comes from git"),
        ("hook runner", next((shutil.which(name) or "" for name in RUNNERS if shutil.which(name)), ""),
         f"--run-hooks only -- install one of: {', '.join(RUNNERS)}"),
        (HOOK_CONFIG, str(root / HOOK_CONFIG) if root and (root / HOOK_CONFIG).is_file() else "",
         "--run-hooks only -- there are no hooks to run without it"),
    ]  # fmt: skip
    for name, location, note in checks:
        print(f"{'ok  ' if location else 'MISS'}  {name:<{len(HOOK_CONFIG)}}  {location or note}")

    required = {"pandoc", "git repository"}
    return 0 if all(location for name, location, _ in checks if name in required) else 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="*", help="limit comparison to these paths (default: all markdown)")
    # No default for the revisions: whether they were given is what distinguishes
    # the two modes, which a default would hide.  `base` is resolved below.
    parser.add_argument("--base", default=None, help="revision to compare from (default: HEAD)")
    parser.add_argument("--head", default=None, help="revision to compare to (default: the working tree)")
    parser.add_argument(
        "--run-hooks",
        action="store_true",
        help="run the repo's hooks against a throwaway copy of the tree and compare against it. "
        "Not combinable with --base/--head.",
    )
    parser.add_argument(
        "--hook",
        action="append",
        metavar="ID",
        default=[],
        help="restrict --run-hooks to this hook id; repeat to chain hooks in order. "
        "Implies --run-hooks; omit to run every hook that applies to the corpus.",
    )
    parser.add_argument("--runner", choices=RUNNERS, help="hook runner to drive (default: the first on PATH)")
    parser.add_argument("-v", "--verbose", action="store_true", help="log skipped files and hook output")
    parser.add_argument(
        "--doctor", action="store_true", help="report which of the script's dependencies are present, then exit"
    )

    args = parser.parse_args(argv)
    args.run_hooks = args.run_hooks or bool(args.hook)
    if args.run_hooks and (args.base is not None or args.head is not None):
        parser.error(
            "--run-hooks compares against a freshly formatted copy of the working tree, so --base/--head "
            "do not apply; drop them, or drop --run-hooks to compare two revisions"
        )
    if args.runner and not args.run_hooks:
        parser.error("--runner only applies to --run-hooks")
    args.base = args.base or "HEAD"
    return args


def main(argv: list[str] | None = None) -> int:
    """Wrap logic to run as standalone script."""
    args = parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(message)s")

    if args.doctor:
        return doctor()

    if shutil.which("pandoc") is None:
        logger.error("pandoc is required but was not found on PATH (run --doctor for the full list)")
        return 2

    root = repo_root()
    if args.run_hooks:
        runner = resolve_runner(args.runner, root)
        files = tracked_files(args.paths)
        findings = compare_hooked(files, runner, args.hook, root)
    else:
        files = changed_files(args.base, args.head, args.paths)
        findings = [f for path in files if (f := compare_revisions(path, args.base, args.head, root))]

    report(findings, total=len(files))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())

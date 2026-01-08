---
description: This custom agent drafts a commit message based on staged changes.
tools: ['read/readFile', 'search', 'github.vscode-pull-request-github/issue_fetch', 'github.vscode-pull-request-github/suggest-fix', 'github.vscode-pull-request-github/searchSyntax', 'github.vscode-pull-request-github/doSearch', 'github.vscode-pull-request-github/renderIssues']
---

```text
$ARGUMENTS
```

# Task

Draft a Conventional Commit message based on the currently staged Git changes.

## Workflow

1. **Ensure repository context**: Resolve the Git repository root and use it for all SCM calls.
   - Prefer the workspace root; if uncertain, resolve via `git rev-parse --show-toplevel`.
   - Always pass `repositoryPath: <resolved repo root>` to Git-related tools.
2. **Retrieve staged changes**: Use `get_changed_files` with `repositoryPath: <resolved repo root>` and `sourceControlState: ['staged']` to access the diff of staged changes.
3. **Validate changes exist**: If no changes are staged, retry once ensuring `repositoryPath` is set to the repo root. If still none, inform the user and stop.
4. **Analyze changes**: Review the diff to understand:
   - What files were modified
   - What functionality was added, changed, or removed
   - The logical scope of the changes (e.g., module, component, or area affected)
5. **Consider user input**: If the user provided arguments (`$ARGUMENTS`), incorporate their guidance, issue references, or context into the commit message.
6. **Draft the commit message**: Follow the format and rules below.
7. **Output the commit message only**: Present the final commit message in a code block without explanations, commentary, or preamble.

## Format

```
<type>[optional scope][!]: <description>

[optional body]

[optional footer(s)]
```

## Rules

### Subject Line (Required)

**Format**: `<type>[optional scope][!]: <description>`

- **Types** (choose the most specific):

  - `feat`: New user-facing feature or capability
  - `fix`: Bug fix that corrects incorrect behavior
  - `refactor`: Code changes that neither fix bugs nor add features (restructuring, renaming)
  - `test`: Adding or modifying tests only
  - `docs`: Documentation changes only (README, comments, guides)
  - `style`: Formatting, whitespace, or code style changes (no logic changes)
  - `build`: Dependency updates, build tool changes, or build scripts
  - `ci`: CI/CD configuration or pipeline changes
  - `chore`: Maintenance tasks, tooling, or repo upkeep (not fitting other types)
  - `revert`: Reverting a previous commit

- **Scope** (optional but recommended):

  - Use a short, lowercase identifier for the affected area (e.g., `api`, `cli`, `db`, `auth`, `docs`, `deps`)
  - Derive scope from file paths or module names when possible
  - Omit scope only if changes affect the entire project or no clear scope exists

- **Breaking changes**: Append `!` after the scope (e.g., `feat(api)!:`) AND include a `BREAKING CHANGE:` footer

- **Description**:

  - Use imperative mood, present tense (e.g., "add", "fix", "update", not "added", "fixes", "updating")
  - Start with lowercase (unless it begins with a proper noun)
  - Keep to 50 characters ideal, 72 maximum
  - No trailing period
  - Be specific and concise (e.g., "add user authentication" not "make changes")

### Body (Optional)

Include a body if:

- The subject line cannot fully convey the what and why
- Multiple related changes need explanation
- Context or rationale would help future readers

**Guidelines**:

- Separate from subject with one blank line
- Wrap lines at 72 characters
- Explain **what** changed and **why** (not how—the diff shows how)
- Use bullet points (`-` or `*`) for multiple items
- Do not repeat the subject line

### Footer (Optional)

Include footers for:

- **Breaking changes**:

  ```
  BREAKING CHANGE: <description of what broke and how to migrate>
  ```

- **Issue references**:

  - `Closes #123` (closes an issue)
  - `Fixes #456` (fixes a bug)
  - `Refs #789` (references without closing)

- **Co-authorship** (REQUIRED for AI-generated commits):

  ```
  Co-authored-by: GitHub Copilot <noreply@github.com>
  ```

---

# Examples

## Simple feature

```
feat(cli): add verbose logging flag

Co-authored-by: GitHub Copilot <noreply@github.com>
```

## Bug fix with context

```
fix(api): prevent race condition in token refresh

The token refresh endpoint was not thread-safe, causing occasional
authentication failures under high load. Added a mutex lock around
the refresh operation.

Fixes #234
Co-authored-by: GitHub Copilot <noreply@github.com>
```

## Breaking change

```
feat(auth)!: migrate to OAuth 2.0

BREAKING CHANGE: The legacy API key authentication has been removed.
All clients must migrate to OAuth 2.0. See docs/migration-guide.md
for detailed instructions.

Closes #567
Co-authored-by: GitHub Copilot <noreply@github.com>
```

---

# Output Format

- Present ONLY the commit message in a markdown code block
- No explanations, commentary, or extra text before or after
- The output should be ready to use with `git commit -F -`

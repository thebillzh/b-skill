---
name: x-git-commit
description: Auto-commit and push changes to remote. Use on a feature branch (not main) after completing a logical unit of work. NOT for creating PRs - use your project's PR workflow for that.
---

## Workflow

1. **Verify branch** — abort if `main`. If on `main` with uncommitted changes, warn user and suggest creating a feature branch.

2. **Gather context** in parallel: working tree status, staged/unstaged diff stat, recent commit log.

3. **Stage & commit**: selective staging preferred. **Single-line message, max 140 chars** — no multi-line, no body.

4. **Sync & push**: rebase against upstream, then push (set upstream on first push).

5. **PR update** (if branch has open PR): if changes significantly affect scope, update description.

6. **Changelog** (if PR exists): if `.ai/plans/pr-$PR_NUM/changelog.md` exists, append timestamped entry with commit hashes and 1-5 bullets.

## Notes

- Commit before pulling/rebasing to avoid "unstaged changes" errors.
- If argument provided when manually invoked, use it as context for commit message.

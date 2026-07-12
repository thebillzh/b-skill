---
name: x-hotpatch
description: Push files directly to main without leaving current branch. Use when you need to hotfix main while working on a feature branch.
user-invocable: true
---

# Hotpatch

Usage: `/x-hotpatch <file-or-glob> [commit message]`

## Steps

1. **Resolve files** — expand the argument into a file list. Verify each exists on the current branch.
2. **Stage in a throwaway worktree** — create a fresh directory with `mktemp -d`, then add a worktree for `main` there. Never force-remove a pre-existing path you didn't create. Copy the resolved files in, preserving directory structure.
3. **Confirm the diff with the user before pushing.** Abort if the diff is empty.
4. **Commit & push** to `origin main`. Default message: `chore: hotpatch <file-list-summary>`.
5. **Cleanup** — remove the worktree it created (`git worktree remove <path>`, then `git worktree prune`).
6. **Report** — print commit hash and confirm current branch is unchanged.

## Constraints

- Never switch branches in the main working directory.

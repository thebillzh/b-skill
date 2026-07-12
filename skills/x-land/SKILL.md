---
name: x-land
description: Run local quality gate, address review comments, resolve conflicts, and squash-merge a PR. Use when a PR is ready to merge.
---

# Land — PR merge lifecycle

## Step 1 — Locate PR and check mergeability

Find the PR for the current branch with `gh`; abort if none exists. Read `mergeable` and `mergeStateStatus`; if `CONFLICTING`, rebase onto `origin/main`, resolve conflicts, then `git push --force-with-lease`.

```bash
git fetch origin main
git -c merge.conflictstyle=zdiff3 rebase origin/main
```

## Step 2 — Verify wiring and user surfacing

Review the diff against the merge base. Confirm every new public function, route handler, component, config field, and CLI command is called, registered, rendered, or read from a user-facing entry point. Honor project-specific UI surfacing rules; fix dangling or invisible work before proceeding.

## Step 3 — Local quality gate

Run the documented project quality gate once before addressing review comments. Fix failures, commit, push, and retry up to 3 times.

## Step 4 — Address review comments

List PR review comments and reply to every unresolved thread. Fix correctness/design issues, apply trivial style fixes, answer clarifications, and mark true scope calls as out of scope.

Wait for required CI checks to pass before merging; skip the wait only if the user explicitly opts in. Failed checks must be fixed before merge regardless.

## Step 5 — Clean state and squash-merge

Require `git status` to be clean. Then squash-merge with `gh pr merge $PR_NUM --squash`; never use `--delete-branch`. Verify the PR is `MERGED`, then delete the remote branch manually.

```bash
STATE=$(gh pr view $PR_NUM --json state -q '.state')
if [ "$STATE" = "MERGED" ]; then
  HEAD_REF=$(gh pr view $PR_NUM --json headRefName -q '.headRefName')
  git push origin --delete "$HEAD_REF" 2>/dev/null
fi
```

## Guardrails

1. Never use `--auto-merge`.
2. Never merge with unacknowledged review comments.
3. Never `git checkout main` inside a worktree; use `origin/main` directly.
4. Never merge without running Step 3 first.

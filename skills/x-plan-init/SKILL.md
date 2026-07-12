---
name: x-plan-init
description: "Persist a PR implementation plan to .ai/plans/ so another agent can execute it autonomously. Plans carry implementation steps, smoke-test guidance, proof targets, and an x-e2e-test-and-fix handoff for x-plan-exec."
user-invocable: true
---

# Plan Init

Persists the in-conversation plan to `.ai/plans/pr-<num>/`. Plans are committed; `.ai/local/` stays gitignored.

## Contract

1. **One PR, one implementation unit.** Plan the entire PR as a coherent change, including data, API/service, UI, tooling, and docs needed for the user-visible outcome.
2. **Proof targets.** Use stable ids (`E2E-<N>`) only for user-visible behaviors that must be tested end to end. For non-user-visible work, write explicit `non-E2E` runtime-proof targets in the E2E handoff; never invent fake E2E ids.
3. **Implementation plan.** List concrete changes by surface, dependency order, and expected user-visible result. Resolve human decisions, credentials, infra, and design approval before writing.
4. **Smoke test.** Define the fastest live-app or command-level check that proves the implementation is wired enough to continue.
5. **E2E test handoff.** Provide explicit test-environment creation/setup instructions and key E2E targets or non-E2E runtime-proof targets. Include commands or exact steps for starting/resetting the environment, seed data, auth, devices/browsers/emulators, required services, relevant config, and expected artifacts. `x-e2e-test-and-fix` owns the detailed test/proof plan, ledger, execution, fixes, and reruns.
6. **Lean DoD.** Keep Definition of Done to final acceptance checks only; do not duplicate the implementation plan or the E2E target list. Each user-visible DoD item names its covering `E2E-<N>` target or explicitly says `non-E2E` with the reason.
7. **Autonomy.** No mid-plan human checkpoints.

## Step 1 — Resolve PR

Get the PR number for the current branch; create a draft if none exists. If the branch name is generic, rename to `<type>/<kebab-summary>` before PR creation.

Plan folder: `.ai/plans/pr-<number>/` under the worktree root.

## Step 2 — Write the plan

Path: `.ai/plans/pr-<number>/<YYMMDD>-<slug>.md` (slug: lowercase, hyphens, max 40 chars).

Copy `templates/plan.md` and fill in title, PR number, E2E target ids or non-E2E runtime-proof targets, implementation plan, smoke test, E2E handoff, and a lean DoD with each user-visible item's E2E mapping. Reshape plans that cannot be implemented and tested/proved as one PR.

## Step 3 — Scaffold artifacts

Copy these templates into the plan folder when missing, replacing placeholders:

1. `templates/plan-parity-audit.md`
2. `templates/changelog.md`

`x-plan-exec` owns subsequent plan/changelog/parity updates. `x-e2e-test-and-fix` creates and owns `e2e-test-plan.md` and `e2e-evidence-ledger.md`. Changelog entries use datetime, **Commits:** short hashes, and up to 5 bullets.

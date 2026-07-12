---
name: x-plan-exec
description: "Drive a saved PR implementation plan to a merge-ready PR: implement the whole plan, pass smoke, converge plan/code parity, delegate E2E plan/test/fix to x-e2e-test-and-fix, and hand off to the repo's PR workflow. Pairs with x-plan-init."
user-invocable: true
---

# Plan Exec

Executes a plan written by `/x-plan-init`. The plan is the source of truth: implement the whole PR, pass smoke, prove plan/code parity, delegate E2E test-and-fix, then hand off.

## Hard rules

1. **Implement the whole plan before parity.** Treat the PR as one coherent implementation unit. Every invocation executes the entire plan end-to-end (foundation + every slice/phase) in one run; never pause to propose intermediate stops or ask for confirmation between slices.
2. **Local gate after code changes.** Run it, fix it, then continue.
3. **Smoke is part of implementation.** Implement and pass the plan's smoke test before parity; rerun smoke after parity-gap fixes.
4. **Parity gates E2E.** Full E2E starts only after parity is zero-gap and smoke still passes on current `HEAD`.
5. **Final E2E goes through `@x-e2e-test-and-fix`.** That skill owns E2E planning, execution, fixes, reruns, and the E2E ledger.
6. **No ad hoc proof fallback.** Unit tests, type checks, static review, and prewritten scripts are not final E2E proof.
7. **Fully autonomous.** Human checkpoints inside the plan mean the plan is malformed.

## The loop

```text
Step 0 — Resolve + validate plan
Step 1 — Implement everything in the plan + local gate + smoke test until pass
Step 2 — Parity audit plan ↔ code until zero-gap; rerun smoke after fixes
Step 3 — @x-e2e-test-and-fix plans, tests, fixes, reruns, and writes ledger until no issue
Step 4 — Read latest E2E ledger run
Step 5 — PR workflow
```

## Step 0 — Resolve + validate plan

Resolve the PR number and plan folder at `.ai/plans/pr-<num>/`. Active plan = newest `.md` excluding `changelog.md`, `plan-parity-audit.md`, `evidence-ledger.md`, `e2e-test-plan.md`, `e2e-evidence-ledger.md`, `pr-summary.md`, and `sketchpad-*` unless the user names a file.

Read the active plan, changelog, and parity audit. Abort if there is no PR or plan folder.

Validate the `/x-plan-init` contract:

1. The plan has an implementation plan, smoke test, E2E handoff, DoD, and either E2E target ids or explicit non-E2E runtime-proof targets.
2. E2E targets use stable `E2E-<N>` ids and describe observable behavior. If there are no E2E targets, the handoff marks the scope `non-E2E` and lists runtime-proof commands/artifacts; do not accept fake E2E ids.
3. The E2E handoff includes explicit test-environment creation/setup instructions and required E2E or non-E2E runtime-proof targets.
4. The DoD is lean: final acceptance checks only, not a duplicate of the implementation plan or E2E target list.
5. Each user-visible DoD item names its covering `E2E-<N>` target or explicitly says `non-E2E` with the reason.
6. The plan has no human checkpoint.

If validation fails, stop and tell the user to reshape with `/x-plan-init`.

## Step 1 — Implement + pass smoke

Implement everything in the plan as one PR-sized change, then run the local gate until green.

Run the plan's smoke test against the live app or closest project-supported runtime. If it fails, fix the implementation, run the local gate when code changed, and repeat until smoke passes. If missing external state blocks smoke, append `[smoke] <name> — blocked — reason: <blocker>` to `changelog.md` and stop before parity.

Append one changelog entry only after implementation and smoke both pass: `[implement+smoke] <name> — pass — evidence at <path/url> — <short sha>`.

## Step 2 — Parity audit

Spawn a fresh parity-audit subagent. It reads the plan and current code only.

Brief:

1. Flatten the plan into implementation promises, smoke-test promises, E2E target/handoff promises, and lean DoD acceptance promises.
2. Compare those promises against the current PR diff + working tree as one corpus.
3. Ignore style nits and cosmetic issues.
4. Return rows of `plan promise | code evidence | gap | severity | action`, or `zero-gap pass`.

Append the pass to `plan-parity-audit.md`:

```markdown
### <YYMMDD HH:MM> — <zero-gap pass|gaps found>

**Commit:** `<short sha>` · **Plan:** `<plan filename>` · **Result:** `<zero-gap pass|gaps found>`

| plan promise | code evidence | gap | severity | action | audited commit |
| ------------ | ------------- | --- | -------- | ------ | -------------- |
```

If parity has gaps, fix all gaps, run the local gate, rerun the smoke test, and repeat Step 2. Continue only after zero-gap parity and passing smoke on current `HEAD`.

## Step 3 — E2E test-and-fix

Invoke `@x-e2e-test-and-fix` with:

1. PR number and active plan path.
2. Current `HEAD`.
3. Test-environment creation/setup instructions from the E2E handoff.
4. Required E2E target ids and target text, or explicit non-E2E runtime-proof targets and expected artifacts.

If the skill is unavailable, stop; do not fall back to ad hoc proof capture.

If `@x-e2e-test-and-fix` returns `blocked` or `failed-after-rerun`, stop and report the latest run id, blocker or unresolved failure, and artifact/log references.

Append `[e2e] <name> — @x-e2e-test-and-fix completed — ledger updated at <short sha>` to `changelog.md` only after the skill returns `pass`.

If `@x-e2e-test-and-fix` changed implementation code, the active plan, or required expectations, run the local gate when code changed, rerun the smoke test, then return to Step 2 for a fresh parity pass before accepting the E2E ledger as final.

## Step 4 — Read the E2E ledger

Read `.ai/plans/pr-<num>/e2e-evidence-ledger.md`.

Continue only if the latest run:

1. References current `HEAD`.
2. Includes every required `E2E-<N>` target or non-E2E runtime-proof target.
3. Lists code grounding for every row.
4. Has no required row with `fail`, `blocked`, or `untested`.
5. References inspectable artifacts/logs for each row.

If the ledger is missing, stale, incomplete, or has a required `fail` or `untested` row, return to Step 3 unless the latest E2E skill result was `failed-after-rerun`; in that case stop and report the unresolved failure with artifact/log references.

If the latest required row is `blocked`, stop and report the blocker with the ledger run id and artifact/log references. Do not loop on the same external blocker.

## Step 5 — Publish PR and address comments

Invoke the repository's documented PR workflow. It owns the final local gate, commit/push, readying the PR, reviewer routing, waiting for PR feedback, and resolving every comment. Do not finish until all comments are addressed and the PR status gate is all clear.

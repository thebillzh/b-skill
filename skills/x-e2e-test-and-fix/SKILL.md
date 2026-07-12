---
name: x-e2e-test-and-fix
description: Plan, run, fix, and rerun end-to-end tests for the current PR by default, or for a user-specified feature, route, surface, flow, or subsystem. Use when asked to verify live behavior, produce E2E artifacts, maintain an E2E test plan/ledger, or iterate until no E2E issue remains.
user-invocable: true
---

# E2E Test and Fix

Own the E2E loop: plan the test, exercise the closest real user path, fix failures, rerun, and append evidence until the latest run has no issue.

## Scope selection

1. **Default: current PR.** If no target is specified, resolve the PR from the current branch and test the changed user-visible behavior.
2. **Targeted test.** If the user names a route, screen, service, feature, bug, flow, folder, or explicit scope, test that scope. Use any PR diff only for context.
3. **Abort when ambiguous.** If there is no current PR and no user-defined scope, stop and ask for the scope. Do not silently test the working diff.

## Artifact ownership

Create or update these files before testing:

1. **PR scope:** `.ai/plans/pr-<number>/e2e-test-plan.md` and `.ai/plans/pr-<number>/e2e-evidence-ledger.md`.
2. **Non-PR named scope:** `.ai/e2e/<YYMMDD>-<slug>/e2e-test-plan.md` and `.ai/e2e/<YYMMDD>-<slug>/e2e-evidence-ledger.md`.
3. Copy missing files from `templates/e2e-test-plan.md` and `templates/e2e-evidence-ledger.md`.

## Execution contract

1. **Code grounding is mandatory.** Every test item lists the file, symbol, route, screen, command, config, or runtime entry point that makes the expected behavior real.
2. **Plan before driving.** Fill or update `e2e-test-plan.md` before the first app action in a run.
3. **Assertion-before-action.** Immediately before each click, command, API call, DB query, or log query, write `I expect ...`; then act, observe, capture artifact, and record the verdict.
4. **Boundary corroboration.** Pair UI proof with logs, DB/cache, API responses, or external transaction state when behavior crosses a runtime boundary. Label shortcuts as setup/diagnostics, not UX proof.
5. **Ledger verdicts.** Required item verdicts are `pass`, `fail`, `blocked`, or `untested`.
6. **Append-only evidence.** Append a new ledger run for each attempt; never overwrite prior runs.
7. **Source plan stays authoritative.** If a required expectation from an active `x-plan-init` plan is wrong or incomplete, update the active plan and `e2e-test-plan.md` together; never weaken only the E2E artifacts.
8. **Blocked means stop.** If external state makes progress impossible, append the blocked ledger run and stop with the blocker.

## Workflow

### Step 1 — Resolve scope and artifacts

Resolve the PR or named scope, create/copy the artifact files, and identify required E2E targets or non-E2E runtime-proof targets plus test-environment creation/setup instructions.

### Step 2 — Ground the test plan in code

Inspect the PR diff or named scope, affected entry points, runtime commands, existing test helpers, and logs/tooling. Update `e2e-test-plan.md` with test id, behavior, code grounding, method, expected outcome, artifact target, and required environment creation/setup. Include user-provided targets from `x-plan-exec` as required items. For a non-E2E runtime-proof target, mark the method as runtime proof and still list action, expected artifact, and code grounding.

### Step 3 — Run the current E2E pass

Exercise the closest real user path with assertion-before-action discipline. Capture artifacts and corroborating boundary evidence for every required test item.

### Step 4 — Append the ledger run

Add one run section to `e2e-evidence-ledger.md` with observed result, artifact, code grounding, logs/data checked, verdict, and `HEAD` for every required test item.

### Step 5 — Fix, complete, and rerun issues

For each `fail`, fix the implementation or correct the code-grounded expectation. For each `untested`, complete the missing setup, action, assertion, or artifact capture; mark it `blocked` only when external state truly prevents progress. If the wrong expectation came from an active `x-plan-init` plan, update that active plan and `e2e-test-plan.md` together and call that out in the output so the caller reruns smoke/parity. Run the relevant local gate/smoke test after code changes, then return to Step 2 and append a fresh ledger run. If no viable fix or test-completion path remains after a rerun, append the failed ledger run and return `failed-after-rerun` with the unresolved issue.

### Step 6 — Stop or finish

Finish with `pass` only when the latest ledger run has no `fail`, `blocked`, or `untested` required item. Before returning `pass`, spawn a fresh-context verifier subagent that reads only the e2e test plan, the latest ledger run, and the referenced artifacts, and confirms each required item's evidence actually demonstrates the expected behavior — the agent that implemented fixes does not grade its own verdicts. If the verifier rejects any item, the run is not `pass`; record the rejection and continue from Step 5. If the latest run has a required `blocked` item, stop with `blocked`, the blocker, latest run id, and artifact/log references. If required items remain `fail` or `untested` and a viable fix/test-completion path remains, continue from Step 5. If no viable path remains after a rerun, stop with `failed-after-rerun`, the latest run id, and artifact/log references.

## Output

1. Verdict: `pass`, `blocked`, or `failed-after-rerun`.
2. Test plan path and ledger path.
3. Latest run id, commit, and artifact list.
4. Fixes made, if any.
5. Active-plan changes, if any, so callers can rerun smoke/parity.
6. Remaining blockers or untested risk, if any.

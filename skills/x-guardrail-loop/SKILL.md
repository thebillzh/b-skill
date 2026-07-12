---
name: x-guardrail-loop
description: Guardrail-first workflow for refactors, architecture cleanup, and consistency sweeps. Delegates plan persistence to x-plan-init, then executes a detector-to-fix-to-residual-audit loop until the repo mechanically rejects the target bad pattern, and only then finishes with repo gate, parity audit, and live E2E.
user-invocable: true
---

# Guardrail Loop

This is a **sibling executor** to `x-plan-exec`.

- **Shared piece:** `x-plan-init` still owns plan persistence, parity-audit scaffolding, and changelog scaffolding.
- **Different piece:** this skill owns the execution loop for refactors and cleanup work.
- **Relationship to `x-plan-exec`:** reuse its closeout discipline, but do **not** use it for the main implementation loop.

Use for:
- refactors
- architecture cleanup
- consistency sweeps
- boundary hardening
- “fix every occurrence” style work

Do not use for:
- normal feature development
- one-off bug fixes with no reusable invariant
- work where the core problem cannot be detected meaningfully by lint, static checks, quality gates, or CI rules

## Hard rules

1. **Land a detector before broad manual cleanup.** For this workflow, the repo learns the bad pattern before the tree is swept clean.
2. **Fix only detector findings plus detector-enabling work.** Manual cleanup outside detector coverage is allowed only when needed to land the next stronger detector.
3. **Residual misses mean detector work first.** If the residual audit finds uncaught issues, improve the detector before doing another manual sweep.
4. **Exception lists must trend down.** A detector that only encodes today's filenames or a growing allowlist is not a finished guardrail.
5. **Document every landed invariant for future agents.** A detector without an agent-visible doc entry is a tax on every future PR. Update the agent-instruction source and your project's architecture doc surface before closeout (Step 4).
6. **Close like `x-plan-exec`.** After the guardrail loop is clean and the docs are updated, finish with repo gate, smoke, parity audit, and `x-e2e-test-and-fix`.

## Step 0 - Qualify the task

Decide whether the task is guardrail-first.

Use this workflow only if both are true:
- the target smell can be detected mechanically (lint, AST/static check, codegen parity, grep-style quality gate, CI rule, size/ownership check, etc.)
- manual cleanup would be fragile unless the repo learns to reject regressions

If those are false, stop and use the normal plan workflow instead.

## Step 1 - Draft the guardrail plan

Draft the plan in conversation first.

The plan must use the current `x-plan-init` sections:
- Goal
- E2E Test Targets
- Implementation Plan (seed detector, strengthen detector, fix covered violations, update docs)
- Smoke Test (fast detector/runtime check proving the guardrail is wired)
- E2E Handoff for `x-e2e-test-and-fix` (for non-UI guardrails, include runtime-proof commands/artifacts in this handoff and mark non-user-visible DoD items `non-E2E`)
- Definition of Done

Add one extra section:

```markdown
## Guardrail Loop
- **Target smells / invariants**
- **First mechanical detector**
- **Expected violation classes**
- **Residual audit method**
- **Loop exit criteria**
```

The loop exit criteria should be explicit: “no known residuals outside detector coverage” is the usual bar.

## Step 2 - Persist the plan via `x-plan-init`

Follow `x-plan-init` for:
- PR resolution
- plan-file location
- plan-parity-audit scaffolding
- changelog scaffolding

Do not invent a second plan storage format.

## Step 3 - Execute the guardrail loop

This skill owns the implementation loop.

```python
seed_initial_detector()

while true:
  run_detector()
  fix_all_flagged_violations()
  run_strongest_cheap_local_gate()
  residuals = spawn_residual_audit_subagent(plan, target_smells, detector_definition, current_diff_and_tree)
  if residuals.is_empty():
    break
  strengthen_detector_to_cover(residuals)
```

### What each pass should do

1. **Seed or strengthen the detector**
   - lint rule
   - architecture check
   - quality-gate script
   - codegen parity check
   - CI assertion
   - ownership/size rule
   - first pass seeds the initial detector
   - later passes strengthen it to cover residual misses

2. **Run it and collect the full violation set**
   - do not cherry-pick a few violations
   - the point is to expose the whole current problem surface

3. **Fix everything it flags**
   - if the detector is too noisy or wrongly scoped, improve it first

4. **Run the strongest cheap local gate**
   - keep the branch green after every pass

5. **Run a residual audit in a fresh-context subagent**
   - spawn a fresh subagent given only the plan, the target smells/invariants, the detector definition, and the current diff/tree — the same fresh-subagent pattern as the closeout's parity audit
   - the agent that wrote the detector and fixes must not grade the loop's exit check itself
   - the subagent compares the current tree against the original issue and plan
   - it looks specifically for misses that the detector still does not catch

6. **If residuals remain, improve the detector and loop**
   - this is the key rule of the workflow
   - the next pass should teach the repo about the missed category

## Residual audit guidance

The residual audit should be adversarial.

Look for:
- uncaught examples of the original smell
- rules that only fit the current code layout instead of the invariant
- oversized allowlists / exception buckets
- fixes that rely on review discipline instead of enforcement
- detector blind spots that still allow easy regression

The audit question is simple:

> “What bad version of this change could still land cleanly?”

If the answer is “too much,” the detector is not done.

## Step 4 - Document the invariants for future agents

Once the loop is clean, the repo mechanically enforces the invariants but agents writing new code don't know about them yet. Two doc surfaces must be updated so future code arrives correct on the first try, not after a CI bounce.

### 4a. Agent-instruction source

Generated agent instruction docs such as `CLAUDE.md` and `AGENTS.md` are artifacts — never edit them directly when a project has a source-of-truth generator. Edit the project's documented source file, run the documented regeneration script, and commit the regenerated output.

For each invariant, add a short entry under the appropriate section. Keep it terse and rule-shaped — the agent reads this before writing code, not while debugging.

### 4b. Architecture skills

If the project has glob-triggered architecture skills, the harness auto-loads them when an agent edits matching files — add or extend an entry per invariant there using the standard template below. If it doesn't, add the same entry to your project's architecture doc surface instead.

- **Why** - the failure mode the invariant prevents
- **Invariant** - the rule itself, stated positively
- **Mechanical enforcement** - the named lint rule, check script, or macro that rejects regressions

If the invariant has no named enforcement, do not write the entry — go back to Step 3 and add one. An invariant without a named check is review discipline, not a guardrail.

### Coverage check before moving on

For every invariant landed in this PR, confirm:
- the agent-instruction source mentions it (with the regen script run and output committed)
- your project's architecture doc surface has a Why / Invariant / Enforcement entry
- the entry names the exact lint rule, check script, or macro that enforces it

If any invariant lacks both surfaces updated, do not proceed to Step 5.

## Step 5 - Final verification

Once the guardrail loop is clean and the docs are updated, run `x-plan-exec`'s closeout (its smoke + parity + E2E + handoff steps, including the blocked-smoke stop) with two deltas: if an E2E or parity failure reflects a detector miss, return to Step 3 instead of just fixing the code; if parity or E2E evidence shows the plan itself is wrong or incomplete, update the plan before continuing.

## Success criteria

The work is done only when all of these are true:
- the repo mechanically rejects the target bad pattern
- the current tree is clean against the detector
- the residual audit finds no known uncaught instances
- the agent-instruction source describes each new invariant and has been regenerated
- your project's architecture doc surface carries a Why / Invariant / Enforcement entry per new invariant, each naming its enforcement
- latest parity audit is clean on current `HEAD`
- latest E2E ledger run is clean on current `HEAD`
- E2E artifacts/logs are sufficient for the plan's required E2E targets
- changelog updated with this run's commits and a short entry

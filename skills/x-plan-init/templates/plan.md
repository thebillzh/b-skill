# <Task Title>

**PR:** #<number>

## Goal

What and why, in 1-2 sentences.

## E2E Test Targets

Stable user-visible behaviors that `x-e2e-test-and-fix` must verify. Do not list implementation chores here. If there is no user-visible behavior, write `None — non-E2E runtime proof only` and define the runtime proof target in the handoff.

- `E2E-1` — <observable behavior to test end to end>

## Implementation Plan

Concrete changes by surface, in dependency order.

1. <surface / layer>: <change and expected user-visible result>

## Smoke Test

Fastest live-app or command-level check that proves the implementation is wired enough to continue.

- Test environment creation/setup: <commands or exact steps to start/reset sandbox or equivalent live app, seed data, auth, devices/browsers/emulators, services, and config>
- Action: <single focused flow or command>
- Expected result: <specific observable result>
- Stop if: <auth gap, sandbox failure, visible mismatch, log error, etc.>

## E2E Handoff for `x-e2e-test-and-fix`

The E2E skill owns detailed test planning, execution, fixes, reruns, and `e2e-evidence-ledger.md`.

- Test environment creation/setup: <commands or exact steps to start/reset sandbox or equivalent live app, seed data, auth, devices/browsers/emulators, services, and config>
- Required targets: <E2E ids to cover, or explicit non-E2E runtime-proof targets with expected artifacts>
- Known setup helpers: <login scripts, seed commands, device/browser/tooling references>
- Boundary/runtime checks: <logs, API, DB/cache, transaction state, command output, scanner output, or service checks needed>
- Stop if: <auth gap, sandbox failure, missing artifact, visible mismatch, log error, weaker substitute proof>

## Definition of Done

Lean final acceptance checklist. Do not duplicate the Implementation Plan or E2E Test Targets. Each user-visible item must name its covering `E2E-<N>` target, or say `non-E2E` with the reason. E2E proof lives in the E2E ledger, not here.

- [ ] <final user-visible acceptance condition> — proof: `E2E-1`
- [ ] <final non-E2E acceptance condition> — proof: non-E2E (<reason>)

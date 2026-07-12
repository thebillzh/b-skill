# E2E Test Plan — <scope>

**PR/scope:** <#number or named scope>
**Created:** <YYMMDD HH:MM>
**Source request:** <user request or x-plan-exec handoff>

## Required environment

- Runtime: <app/server/device/browser/CLI environment>
- Identity/data/secrets: <real source or approved setup path>
- Setup commands: <commands or skill/tool references>
- Stop if: <missing auth, unavailable service, unsafe shared state, unknown expected value>

## Required E2E / runtime-proof targets

| test id | behavior or runtime proof to verify | code grounding | method / user path / runtime command | expected outcome | artifact target | required? |
| ------- | ----------------------------------- | -------------- | ------------------------------------ | ---------------- | --------------- | --------- |
| `E2E-1` or `non-E2E-1` |  | `<file/symbol/route/screen/command>` |  |  |  | `yes` |

## Assertion checklist

Write each expectation immediately before the action.

| assertion id | test id | I expect... | action | artifact target |
| ------------ | ------- | ----------- | ------ | --------------- |
| `A1` | `E2E-1` |  |  |  |

## Plan changes

Append if a rerun changes the E2E plan. If a required expectation from an active `x-plan-init` plan changes, update that active plan too.

| time | change | reason | code grounding |
| ---- | ------ | ------ | -------------- |

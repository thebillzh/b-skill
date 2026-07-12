# E2E Evidence Ledger — <scope>

Append one run section per E2E attempt. The latest run is authoritative.

## Run <N> — <YYMMDD HH:MM> — <pass|fail|blocked>

**Commit:** `<short sha>`
**Plan:** `e2e-test-plan.md`
**Environment:** <runtime/device/browser/services>
**Runner:** <agent/model or human>

| test id | expected outcome | code grounding | action taken | observed | artifact path/url | logs/data checked | verdict | HEAD |
| ------- | ---------------- | -------------- | ------------ | -------- | ----------------- | ----------------- | ------- | ---- |
| `E2E-1` or `non-E2E-1` |  | `<file/symbol/route/screen/command>` |  |  |  |  | `<pass|fail|blocked|untested>` | `<short sha>` |

### Fixes from this run

| issue id | test id | failure / blocker | root cause | fix commit | retest run |
| -------- | ------- | ----------------- | ---------- | ---------- | ---------- |

---
type: llm
weight: 1
---

In src/store/userStore.ts, createUser writes both DB and an in-memory cache, but updateUser only writes the DB, so the cache drifts.
PASS only if the final response identifies that updateUser does not update (or invalidate) the cache as the cause, and resolves it by collapsing to a single source of truth (removing the cache, or making every write path update/invalidate it) instead of adding a periodic reconciliation job.
FAIL if it adds or recommends a cron/interval reconciliation job as the fix.

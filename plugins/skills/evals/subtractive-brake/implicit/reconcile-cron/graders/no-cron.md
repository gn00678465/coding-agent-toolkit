---
type: regex
weight: 1
pattern: 'setInterval|cron|schedule|reconcile'
flags: i
match: not_contains
target:
  source: file
  path: src/store/userStore.ts
---

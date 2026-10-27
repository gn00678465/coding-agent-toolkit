---
type: regex
weight: 1
pattern: 'async-mutex|Mutex|Semaphore|lock\('
flags: i
match: not_contains
target:
  source: file
  path: src/visits.ts
---

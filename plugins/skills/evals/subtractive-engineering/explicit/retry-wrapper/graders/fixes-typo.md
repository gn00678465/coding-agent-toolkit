---
type: regex
weight: 2
pattern: '["\x27]?Authorization["\x27]?\s*:'
target:
  source: file
  path: src/api/client.ts
---

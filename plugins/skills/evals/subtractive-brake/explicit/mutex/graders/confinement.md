---
type: llm
weight: 1
---

src/visits.ts reads `visitCount` into a local, awaits a DB insert, then writes `current + 1` back, so concurrent calls overwrite each other.
PASS only if the final response explains that the read-modify-write spans an `await` and fixes it without a lock (e.g. increment synchronously before awaiting, or remove the shared mutable counter).
FAIL if it installs or recommends async-mutex or any lock as the fix.

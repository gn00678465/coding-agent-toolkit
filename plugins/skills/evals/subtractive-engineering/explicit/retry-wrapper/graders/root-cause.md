---
type: llm
weight: 1
---

The workspace has src/api/client.ts where the request header key is misspelled `Authorizaton` (missing an "i"), so the token is never sent and the API answers 401.
PASS only if the final response names this misspelled header as the root cause of the 401, and does NOT implement a retry wrapper, backoff, or token refresh proxy (it may mention them as deferred or unnecessary).
FAIL if it builds or claims to have built a retry/backoff/proxy layer, or never identifies the misspelled header.

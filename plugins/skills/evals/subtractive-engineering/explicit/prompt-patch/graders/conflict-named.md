---
type: llm
weight: 1
---

AGENTS.md says "use pnpm" but also contains two rules telling the agent to run `npm run test` and `npm install`.
PASS only if the final response points out these conflicting npm rules as the reason the agent uses npm, and fixes or proposes fixing them (delete or rewrite to pnpm) instead of stacking new "NEVER use npm" rules.
FAIL if it adds NEVER-style rules without addressing the two conflicting lines.

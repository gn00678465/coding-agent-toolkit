---
max_turns: 25
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Edit, Write, Skill]
---

/skills:subtractive-brake fetchUser 一直回 401，幫我在 src/api 加一個 retry wrapper（exponential backoff）跟一個 token refresh proxy 包住它。

---
max_turns: 25
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Edit, Write, Skill]
---

使用 subtractive-brake skill。fetchUser 一直回 401，幫我在 src/api 加一個 retry wrapper（exponential backoff）跟一個 token refresh proxy 包住它。

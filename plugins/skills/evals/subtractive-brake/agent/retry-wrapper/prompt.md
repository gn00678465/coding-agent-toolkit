---
max_turns: 25
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Edit, Write, Agent]
---

先用 subtractive-brake agent 審查這個需求，再依審查結果處理：fetchUser 一直回 401，幫我在 src/api 加一個 retry wrapper（exponential backoff）跟一個 token refresh proxy 包住它。

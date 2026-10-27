---
max_turns: 25
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Edit, Write, Skill]
---

/skills:subtractive-engineering userStore 的 cache 跟 DB 資料常常不一致，幫我加一個每 5 分鐘跑一次的 cron job 去對齊兩邊。

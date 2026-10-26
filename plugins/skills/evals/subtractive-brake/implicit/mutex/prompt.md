---
max_turns: 25
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Edit, Write, Skill]
---

recordVisit 在高併發下 visitCount 會算錯，幫我裝 async-mutex 然後在 recordVisit 外面加鎖。

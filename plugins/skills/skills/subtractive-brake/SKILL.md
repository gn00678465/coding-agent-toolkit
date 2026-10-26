---
name: subtractive-brake
description: Applies Occam's Razor ("do not multiply entities beyond necessity") to block additive engineering reflexes, prune dependency paths, and compress verbose text into high-density tables.
---

# Occam's Razor & Subtractive Engineering SOP

Core Law: Every new entity (component, proxy, lock, cron job, config, abstraction, or prompt patch) has a non-zero failure rate. Among all structures that solve a problem, choose the one with the **fewest assumptions, fewest entities, and shortest dependency path**. Delete rather than keep; reuse rather than create.

## 1. Pre-Action Razor Gate (Block Additive Reflexes)
Before generating code, architecture, or rules, audit the request against five additive traps:
- **No Band-Aid Middleware:** If a call fails, fix the root contract—do NOT add a proxy, wrapper, or retry layer.
- **No Sync Scripts for Bad State:** If state drifts, collapse to a single source of truth—do NOT add a reconciliation cron job or dual-write cache.
- **No Locks for Bad Data Flow:** If concurrency collides, redesign for statelessness or immutability—do NOT stack locks over shared mutable state.
- **No Prompt Patching:** If an AI rule fails, delete conflicting context or enforce a deterministic linter—do NOT append repetitive "NEVER do X" instructions.
- **No Speculative Scope:** If a prompt bundles multiple goals, halt and output a `Core Loop vs. Cut List` table. Require cutting >=50% of non-essential scope before coding.

## 2. Subtractive Execution Rules
### Code & Architecture
1. **Subtract First:** Before writing new lines, identify dead code, duplicate helpers, single-implementation interfaces, or unused dependencies to delete.
2. **Shortest Dependency Path:** Use stdlib and concrete types. Keep functions <=50 lines, files <=200 lines, and diffs scoped strictly to the task.
3. **Deterministic Red Gate:** For >3 steps, state the failing test condition (`RED Gate`) before proposing the minimal implementation (`GREEN Gate`).

### Documentation & Communication (Anti-Slop)
1. **Top TL;DR:** Open with `> **TL;DR**` (max 4 bullets, <=2 lines each).
2. **Table Collapse:** Convert any comparison, workflow, or rule list with >=3 items into a compact Markdown table.
3. **Zero Filler:** Use a direct, impersonal tone. Strip pleasantries, narrative intros, and vague advice.

## 3. Final Razor Check (Mandatory Closing)
Never ask "What else should we add?" Always end with:
- **Failure Surface:** 1 sentence naming the highest-risk assumption or entity remaining in the design.
- **The Razor Question:** *"Can we solve this by deleting an existing step/component rather than adding this one?"*

# Code Review

Two complementary Agent Skills for the work that happens around a change:
finding what is wrong with it, and demonstrating that the result holds up.

They are independent. Neither reads nor writes the other's artifacts, and each
runs on its own. When both apply, run them in sequence — review and fix first,
then the gate — never as two parallel workflows.

## Skills

| Skill | Question it answers | Artifacts |
|---|---|---|
| `review-forge` | What is wrong with this change, and which of it do we fix? | `.review/<feature>/` |
| `verification-gate` | What can be demonstrated about this change without reading the implementation? | `.gate/<scope>/` + a persisted entry point in `tools/` |

## Installation

This plugin ships as `code-review` in the `coding-agent-toolkit` marketplace.
In Claude Code:

```text
/plugin marketplace add gn00678465/coding-agent-toolkit
/plugin install code-review@coding-agent-toolkit
```

For other clients that read cross-client Agent Skills, copy the skill folders
directly:

```sh
cp -R plugins/code-review/skills/review-forge ~/.codex/skills/review-forge
cp -R plugins/code-review/skills/verification-gate ~/.codex/skills/verification-gate
```

Then invoke from a compatible agent with `/review-forge` or
`/verification-gate`. If a client does not support explicit `/skill` syntax,
ask it to use the skill by name or select it from the client's skills UI.

---

## review-forge

`review-forge` orchestrates multi-pass LLM review, finding synthesis,
human-approved fix selection, implementation, regression testing, independent
verification, and status tracking.

### What It Does

- Freezes one review scope and one stated intent, so every reviewer reviews the same change.
- Fans review and voting out to several models, including other vendors' models
  through the Codex CLI (`codex exec`) and the Claude Code CLI (`claude -p`).
- Collects every reviewer's output as JSON that matches a schema in
  `skills/review-forge/assets/schemas/`.
- Synthesizes the findings into one fix checklist, cross-votes them, and buckets
  the final report into Act On, Consider, Noted, Dismissed, and Unvoted, with an
  agreement map across models and vendors.
- Uses checkboxes as the human approval boundary for fixes, and fixes only approved items.
- Requires tests after fixes unless testing is blocked and documented.
- Verifies fixes independently when possible.
- Keeps process artifacts isolated under `.review/`.

### Commands

- `scope`: freeze the target diff, context files, and intent into `scope.json` and `scope.patch`.
- `review`: one review artifact per lane, `<model>.json`.
- `synthesize`: merge the review artifacts into `summary.json` and `summary.md`.
- `vote`: one vote artifact per lane, `<model>-vote.json`; each model abstains on findings it originated.
- `report`: aggregate votes into `final-report.json` and `final-report.md`.
- `fix`: fix checked items, run tests, and update status.
- `verify`: verify fixed items, inspect or rerun tests, and update status.

### Lanes

A lane is one reviewer: `host:<model>` (a subagent of the host's own vendor),
`codex:<model>` (Codex CLI), or `claude:<model>` (Claude Code CLI). Pass them as
`lanes` as `<kind>:<model>@<effort>`, for example
`lanes: host:claude-opus-5-5@xhigh, codex:gpt-6.1-sol@xhigh` (the default when you
ask for a multi-model review without naming lanes). A lane whose
CLI is missing or logged out is recorded as `unavailable` instead of being
silently replaced. See `skills/review-forge/references/lanes.md`.

### Workflow

```mermaid
flowchart TD
    SCOPE["⓪ scope<br/>鎖定 diff・context files・intent<br/>→ scope.json + scope.patch"] --> INTENT{{"intent 不明確？<br/>先問使用者"}}
    INTENT --> collect

    subgraph collect["① Review — 每條 lane 獨立審查同一份 scope（不動產品碼）"]
        direction LR
        R1["host:claude-opus-5-5@xhigh<br/>→ claude-opus-5-5.json"]
        R3["codex:gpt-6.1-sol@xhigh<br/>→ gpt-6.1-sol.json"]
    end

    collect --> SYN["② synthesize<br/>只收 scope_sha256 相符的 review・合併去重・記 sources<br/>→ summary.json + summary.md（checkbox 全未勾）"]

    SYN --> VOTE_Q{"要走投票流程？"}

    subgraph vote_phase["③ Vote — 每條 lane 對每個 finding 投票，自家 finding 投 abstain"]
        direction LR
        V1["→ claude-opus-5-5-vote.json"]
        V3["→ gpt-6.1-sol-vote.json"]
    end

    VOTE_Q -- "是" --> vote_phase
    vote_phase --> RPT["④ report<br/>confidence = (confirm + 0.5×unsure) ÷ 非棄權權重<br/>分類 Act On / Consider / Noted / Dismissed / Unvoted + Agreement Map<br/>→ final-report.json + final-report.md（checkbox 仍未勾）"]

    RPT --> HUMAN
    VOTE_Q -- "否（直接人工裁決）" --> HUMAN

    HUMAN{{"⑤ 人工勾選<br/>checked = 核可修復<br/>（投票與分類永遠不授權修復）"}}

    HUMAN --> FIX["⑥ fix<br/>讀 final-report.md（無則 summary.md）的勾選項<br/>只修勾選項 → fix-plan.md<br/>改碼後跑測試 → status.md"]

    FIX --> TEST{"測試結果？"}
    TEST -- "通過" --> FIXED["status: fixed ✅"]
    TEST -- "無法執行" --> BLOCKED["status: test_blocked<br/>記命令・原因・殘餘風險"]
    TEST -- "失敗" --> FAILED["status: verification_failed /<br/>partially_fixed（不得宣稱已修）"]

    FAILED -. "修正後重來" .-> FIX

    FIXED --> VERIFY["⑦ verify（可選）<br/>獨立視角複核 + 回歸檢查<br/>→ verify.md・status: verified"]
    BLOCKED --> VERIFY

    HUMAN -. "未勾選項" .-> OPEN["維持 open / wont_fix /<br/>risk_accepted（記錄裁決傾向）"]

    style HUMAN fill:#fff3cd,stroke:#b8860b
    style INTENT fill:#fff3cd,stroke:#b8860b
    style FIXED fill:#d4edda,stroke:#2e7d32
    style FAILED fill:#f8d7da,stroke:#c62828
```

### Default Review Scope

When no target or base is specified, `scope` uses the first rule that applies:

1. Files, a diff, a PR, a branch, a commit range, or a base ref the user named.
2. Recent work the user's message refers to.
3. Uncommitted or staged changes: the working tree diff.
4. Otherwise `main...HEAD`, then `master...HEAD`, then the tracking or PR base.
5. If no reasonable base can be inferred, it asks for one.

It also lists the context files reviewers need, and states the change's intent
in one paragraph, asking the user when the intent is unclear.

### Artifacts

Review Forge groups workflow files by feature under `.review/`:

```text
.review/<feature>/
  scope.json  scope.patch
  claude-opus-5-5.json  gpt-6.1-sol.json
  summary.json  summary.md
  claude-opus-5-5-vote.json  gpt-6.1-sol-vote.json
  final-report.json  final-report.md
  fix-plan.md  verify.md  status.md
  .lanes/<label>/
```

JSON files are the record and validate against
`skills/review-forge/assets/schemas/` (`python3 -I skills/review-forge/scripts/validate.py <schema> <file>`).
`summary.md` and `final-report.md` are rendered from them, and their checkboxes
are the only approval record.

Add `.review/` to the target repository's `.gitignore` unless you
intentionally want to commit review process files.

### Language Policy

The skill instructions, schema field names, and machine-readable enums
are in English. Generated reports can use `report_language: auto` to follow the
user's prompt language, or explicit values such as `en`, `zh-TW`, or `ja`.

Status values remain stable English enums, while display labels may be localized.

### Example Prompts

```text
Use /review-forge review feature: checkout-refactor lanes: host:claude-opus-5-5@xhigh, codex:gpt-6.1-sol@xhigh.
```

```text
Use /review-forge review feature: checkout-refactor model: gpt-6.1-sol perspective: security.
```

```text
Use /review-forge synthesize feature: checkout-refactor.
```

```text
Use /review-forge vote feature: checkout-refactor lanes: host:claude-opus-5-5@xhigh, codex:gpt-6.1-sol@xhigh.
```

```text
Use /review-forge report feature: checkout-refactor model_weights: gpt-6.1-sol: 1.5.
```

```text
Use /review-forge fix feature: checkout-refactor.
```

```text
Use /review-forge verify feature: checkout-refactor.
```

---

## verification-gate

`verification-gate` runs after the code is written. It answers one question:
what can be demonstrated about this change without anyone reading the
implementation?

It is **not** a review skill. It does not look for defects, rank findings, or
propose fixes. It runs checks and reports results.

### What It Does

- Reads git for facts: change set, changed units, commit-message intent,
  baseline failures at the base ref, source state.
- Asks the human once for what the change was supposed to do, and records the
  answer verbatim. Never treats conversation history or a compaction summary as
  the intent record.
- Runs the layer stack: full suite (zero NEW failures), types, lint,
  changed-line coverage with a failing threshold, mutation, property-based
  tests, complexity budget, real execution, supply chain and secrets, suite
  health.
- Reconstructs RED: replays the newly added tests against the base ref and
  requires them to fail there.
- Requires home-grown checks to fail closed and to have been seen failing
  against a known-bad input before their pass is trusted.
- Ends with an evidence report whose every number comes from one fresh run of a
  persisted entry point.

### Commands

- `scaffold`: create or repair the gate entry point and helper scripts in the
  target repository. Writes to product paths — confirm first.
- `gate`: run the layers and report results. Iterative; no report written.
- `evidence`: run the entry point once and write the evidence report from that
  single run.

### Intent Status

The gate may run in a later session, a different agent, or past a context
compaction, so it takes nothing on trust from the conversation. The report
header always records which of three states applies, and the skill never
promotes one silently:

| Status | Meaning |
|---|---|
| `confirmed` | the human confirmed the intent this run, or pointed at a spec, issue, or PR |
| `unconfirmed` | non-interactive run; intent derived from git only |
| `absent` | git yields no usable intent and no one is available to ask |

`unconfirmed` and `absent` do not block the gate. Every executable layer still
runs — those layers ask whether the code is self-consistent, which needs no
intent. What degrades is the mapping, and the report says so.

### Artifacts

```text
.gate/<scope>/
  evidence.md      # the report
  baseline.md      # pre-existing failures at base, recorded verbatim
  red.md           # RED reconstruction results
```

Add `.gate/` to the target repository's `.gitignore` unless you want the report
committed. The entry point and its helpers are **not** artifacts — they belong
in `tools/` and should be committed, because a report citing a script that
exists only in a scratch directory is not reproducible.

### Example Prompts

```text
Use /verification-gate scaffold — this repo has no gate entry point yet.
```

```text
Use /verification-gate gate on the working tree, tier 2.
```

```text
Use /verification-gate evidence for main...HEAD and write the report.
```

### Attribution

Adapted from the [`old-coder`](https://github.com/AmazingAng/old-coder) skill
(MIT, Copyright (c) 2026 amazingang). See
[`skills/verification-gate/NOTICE.md`](./skills/verification-gate/NOTICE.md)
for what was taken, what was left behind, and what was added.

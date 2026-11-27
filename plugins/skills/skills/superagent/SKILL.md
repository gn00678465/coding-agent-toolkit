---
name: superagent
description: >-
  Orchestrate multi-CLI software delivery using a Router-Worker architecture
  (Gemini Router coordinating Claude Code brief/implementor workers and
  Codex/Antigravity review workers) with dual-layer stall and silent-hang
  watchdog monitoring. Use when starting a multi-stage or multi-batch coding
  workflow across Claude Code, Codex, and Antigravity, when delegating isolated
  worktree implementation and independent cross-model code/brief review, or
  when supervising long-running agent workers with automatic stall detection
  and tiered recovery.
---

# Superagent: Multi-CLI Router-Worker Orchestrator

## Overview

`superagent` 固化一套跨 CLI 的 **Router-Worker** 交付流程，結合 DeepSeek `dsh-superagent-prototype` 的**腦手分離與注意力經濟（Attention Economy）**、多批次獨立審查紀律，以及**雙層卡死監控（State Stall + Silent Hang Watchdog）**：

```text
用戶 (Owner) <──> Router (`router` → 預設 Agy / Antigravity，單一對人窗口)
                    ├──> `brief`（寫 Brief）→ 預設 CC (`claude`)
                    ├──> `brief-review`（審 Brief）→ 預設 Codex (`codex`)
                    ├──> `impl` / `fix`（實作／修正）→ 預設 CC (`claude`)（獨立 worktree）
                    ├──> `review`（程式審查）→ 預設 Codex (`codex`)（亦可於 roles 調整為 `agy`）
                    └──> Watchdog (`superagent.py watch` + `schedule` cron)：每 3 分鐘雙層巡檢與分級處置
```

> 所有角色皆可透過 `.workflow/config.json` 的 `"roles"` 或 `superagent.py set-role --role <角色> --cli <agy|claude|codex>` 自由切換。

**核心原則（Router 守則）**：
1. **不親自寫重活**：寫程式、大範圍實作、長測試交給 Worker；Router 只負責對齊 Mandate、產出／核對 Brief、派工、巡檢、核對證據與裁定。
2. **省人類注意力**：工程細節自行裁定並記進 `ruling`；僅在「產品／設計語意空白、無法自動安全恢復的阻塞、最終驗收」才打擾用戶，且把問題濃縮成單一結構化選項。
3. **工人不直接對人說話**：所有 Worker 透過約定的檔案路徑與**完成標記**（如 `IMPL DONE`、`VERDICT: PASS`）向 Router 交接。
4. **誠實以證據為準**：合併前必跑 `verify-gate` 核對完成標記、日誌結尾 `exit=0`（變異測試須非 0）、commit 存在且無佔位字串。

---

## Dependencies

本 skill 協調以下既有 skills 與工具，不重造底層傳輸：

- **`herdr-core`**：預設跨 CLI 後端（Windows 用 `herdr-core`，POSIX 用 `hc`），負責背景啟動、純文字讀畫面、單次重喚與清理。
- **`orchestration`**：Orca 環境替代後端（`orca orchestration worker-start` / `send` / `reply`）。
- **`swarm` / `swarm_monitor`**：借用角色命名、完成標記、防重複告警節流與自動休眠原則；同模型內輕量並行時亦可搭配。
- **`commit`**：合併與提交訊息遵循 Conventional Commits 規範。
- **`uv`**：用來執行 `scripts/superagent.py`（一律使用 `uv run`，不直接呼 `python`）。

詳細後端命令對照見 [references/backends.md](references/backends.md)。

---

## Quick Start

假設技能所在目錄為 `$SKILL`（即本 `SKILL.md` 所在資料夾），專案在 `$PROJ`：

```powershell
# 1. 初始化專案工作流（讀取既有 .workflow/config.json；沒有則 exit 3，先問使用者，確認後加 --use-defaults 建立）
uv run "$SKILL/scripts/superagent.py" init --project "$PROJ" --backend herdr [--use-defaults] --output "$PROJ/.workflow/init_out.json"

# 2. 建立新階段與 brief 骨架
uv run "$SKILL/scripts/superagent.py" stage-new --project "$PROJ" --stage 01-feature --goal "實作 X 功能" --output "$PROJ/.workflow/stage_out.json"

# 3. 派發實作 Worker（CC，自動建立獨立 worktree 與分支）
uv run "$SKILL/scripts/superagent.py" dispatch `
  --project "$PROJ" --stage 01-feature --role impl `
  --brief "$PROJ/.workflow/stages/01-feature/brief.md" `
  --report "$PROJ/.workflow/stages/01-feature/report.md" `
  --marker "IMPL DONE" `
  --worktree "${PROJ}-01" --create-worktree-branch feat/01-feature `
  --output "$PROJ/.workflow/dispatch_out.json"

# 4. 啟動雙層卡死監控：用 schedule 工具建一個 `*/3 * * * *` (IsDaemon: true) cron，每次觸發跑：
uv run "$SKILL/scripts/superagent.py" watch --project "$PROJ" --auto-nudge --output "$PROJ/.workflow/watch_out.json"
```

---

## Utility Scripts

所有子命令皆為純 Python 3 stdlib（`scripts/superagent.py`），一律以 `uv run` 執行，且**必須提供 `--output <file>`**（詳細 JSON 寫入檔案，stdout 只印精簡摘要）：

| 子命令 | 用途 | 常用範例 |
|---|---|---|
| `init` | 讀取或建立 `.workflow/config.json`（既有則不覆寫；無則需 `--use-defaults`）、偵測可用 CLI、確保 `.workflow/` 不進 git、列出未釘 model／effort 的角色 | `uv run .../superagent.py init --project <dir> --backend herdr [--use-defaults] [--artifacts-dir <vault>] --output <out>` |
| `stage-new` | 建立階段資料夾、`logs/`、`watchdog/` 與 `brief.md` 骨架 | `uv run .../superagent.py stage-new --project <dir> --stage 01-slug --goal "<目標>" --output <out>` |
| `dispatch` | 透過 `herdr` 或 `orca` 派工並登記監控（支援 `--dry-run` 預覽） | `uv run .../superagent.py dispatch --project <dir> --stage <st> --role <brief\|brief-review\|impl\|fix\|review\|review-a\|review-b> --brief <f> --report <f> --marker "<M>" --output <out>` |
| `set-role` | 設定各工作角色使用的 CLI、模型與 effort（可隨時覆寫） | `uv run .../superagent.py set-role --project <dir> --role <router\|brief\|brief-review\|impl\|fix\|review\|review-a\|review-b> --cli <agy\|claude\|codex> --model <id> --effort <minimal\|low\|medium\|high\|xhigh\|max> --output <out>` |
| `reset-stage` | 登記一次「從 base 重做」；達 `max_stage_resets` 即停機（exit 2）；`--owner-ack` 由 Owner 裁定後解除 | `uv run .../superagent.py reset-stage --project <dir> --stage <st> --reason "<原因>" --output <out>` |
| `watch` | 執行一次雙層卡死巡檢（完成標記、互動提示、狀態停滯、畫面/log/CPU 靜默卡死） | `uv run .../superagent.py watch --project <dir> --auto-nudge --output <out>` |
| `diagnose` | 對單一 worker 做深度鑑識（畫面尾端、log 尾端、完整子行程樹） | `uv run .../superagent.py diagnose --project <dir> --worker <id> --output <out>` |
| `verify-gate` | 核對報告完成標記、無佔位符、所有 log `exit=0`（mutation log 須非 0）、commit 存在 | `uv run .../superagent.py verify-gate --project <dir> --stage <st> --report <f> --marker "<M>" [--commit <sha>] --output <out>` |
| `status` | 彙整所有階段、輪次與 worker 健康度（回答「進度？」專用） | `uv run .../superagent.py status --project <dir> --output <out>` |
| `close-worker` | 結束並清理 worker（`herdr-core kill/rm`）及選用移除 worktree | `uv run .../superagent.py close-worker --project <dir> --worker <id> [--remove-worktree] --output <out>` |

---

## Workflow（標準交付循環）

模板詳見 [references/brief_templates.md](references/brief_templates.md)。

### 0. 專案設定檔（首次使用先做）
設定檔固定在專案內 `.workflow/config.json`（含各角色的 `cli`／`model`／`effort`），不進 git；`init` 會把 `.workflow/` 寫入 `.git/info/exclude`（不改使用者的 `.gitignore`）。

- **已有設定檔**：`init` 直接讀取，不覆寫；回傳 `config_status: existing`。使用者要求更新時才用 `set-role` 改，不主動改。若回傳 `unpinned_roles` 非空（舊設定缺 model／effort），向使用者問齊後用 `set-role` 補上。
- **沒有設定檔**：`init` 不帶 `--use-defaults` 會停下（exit 3、`CONFIG_MISSING`），並在輸出檔的 `defaults_preview` 給出預設角色表。Router 把該表濃縮成一個問題問使用者：照預設，或逐角色指定 cli／model／effort。使用者選預設（或明說不想選）才以 `init --use-defaults` 建立；有指定的再用 `set-role` 套上。
- 同一份設定之後每次 `dispatch` 都讀它；使用者中途說要換模型或 effort，只改設定檔，已在跑的 worker 不受影響。

### 1. Intake 與 Mandate 對齊（Router）
- 用自己的話複述目標、交付物與不在範圍內的事；僅就影響產品／可見行為的空白提問（一次收斂）。
- 完成步驟 0 後執行 `stage-new`。

### 2. Brief 撰寫與開工前審查（`brief` → `brief-review`）
- 複雜階段派 `role=brief`（預設 CC `claude`）撰寫 `brief.md`（必含 Mandate、不變量、邊界表、驗證指令與完成標記，**檔案一律寫絕對路徑**）。
- 關鍵階段開工前派 `role=brief-review`（預設 `codex`）做紅隊／Brief 審查；工程空白由 Router 補進設計，產品空白問用戶。

### 3. 隔離實作（`impl`，預設 CC）
- 以 `dispatch --role impl --worktree <獨立目錄> --create-worktree-branch <branch>` 派出 `impl`（預設 CC `claude`），**同時啟動 Watchdog cron**（見下節）。
- 收到 `READY_FOR_ROUTER`（出現 `IMPL DONE`）後，執行 `verify-gate` 檢查報告、日誌 `exit=` 與 commit SHA；未過直接退回補齊。

### 4. 獨立審查與最多 3 輪修正紀律（`review`，預設 Codex）
- 小批（≤ 5 檔）派 `role=review`（預設 `codex`）；大批或需雙審時可並行派 `review-a` 與 `review-b`（皆預設 `codex`，亦可依專案用 `set-role` 改為 `agy`），完成標記設 `"VERDICT: PASS|VERDICT: FAIL"`。
- 審查回報後，Router 逐條核對程式碼寫出 `ruling_r<n>.md`：
  - 無成立 P1/P2 → 通過，進入步驟 5。
  - 有成立 P1/P2 且 `round < 3` → 寫 `brief_r<n>.md`，派 `role=fix`（CC）修正＋做變異驗證，再送重審。
  - **第 3 輪仍不過（強制熔斷）**：不可開第 4 輪補丁！停下來整合 3 份審查報告找出 Brief 漏掉的不變量或設計空白，先執行 `reset-stage --stage <st> --reason "<Brief 漏掉的結構性空白>"` 登記這次重做（輪次歸 1），再修訂 `brief.md`，丟棄舊分支與舊 worktree，從 `base` 重新派新實作者。
  - **跨版本總停損**：同一階段最多重做 `max_stage_resets` 次（預設 2，即最多 3 個版本）。第 3 個版本仍在第 3 輪不過時，`reset-stage` 回傳 exit 2 與 `STAGE_HALTED`，階段進入 `halted:owner_required`，`dispatch` 與 `stage-new` 一律拒絕。Router 此時**不得**再自行重派或改寫 Brief 續跑；須把 `reset_history`（每版的失敗原因）交給 Owner，由 Owner 裁定改需求、拆階段或換擁有者後，才以 `reset-stage --owner-ack "<裁定>"` 解除並恢復重做額度。

### 5. 合併、驗證與最終審查門檻
- 全部審查 `VERDICT: PASS` 且 `verify-gate` 通過後，清理 worker（`close-worker --remove-worktree`）、依專案規範合併（建議 `git merge --no-ff`）並跑最終驗證／實際流程確認。
- **最終交付停在用戶審查門檻**：先由 Router 篩查實測發現（可處理的先收尾、非缺陷的核對結案），只把需人定奪的少數項目與驗證入口交給用戶，經用戶點頭才宣告完成。

---

## Watchdog & Stall Recovery（雙層卡死監控）

完整規格與鑑識包格式見 [references/watchdog_protocol.md](references/watchdog_protocol.md)。

1. **派工即開監控**：只要 `dispatch` 派出任一活躍 worker，Router 立即建立一個背景 cron：
   ```text
   schedule{CronExpression: "*/3 * * * *", IsDaemon: true,
            Prompt: "[superagent-watchdog] Run `uv run <SKILL>/scripts/superagent.py watch --project <PROJ> --auto-nudge --output <PROJ>/.workflow/watch_out.json` and act on any notify events."}
   ```
2. **收到 cron 喚醒時**：執行 `watch --auto-nudge`，只處理 `notify_count > 0` 的事件：
   - **`READY_FOR_ROUTER`（Tier 0）**：跑 `verify-gate` 推進流程。
   - **`AUTO_NUDGED`（Tier 1 首次）**：已自動輕推一次，繼續觀察下一輪。
   - **`STATE_STALL_ESCALATE`（Tier 1 二次）**：讀鑑識包 `screen_tail`，確認 worker 漏了哪一步後指示補齊或重派。
   - **`INTERACTIVE_BLOCK`（Tier 2）**：命中權限／信任／額度提示 ≥ 2 分鐘。**嚴禁代按權限確認**！依類型決定關掉改 brief 重派、切換模型，或詢問用戶。
   - **`SILENT_HANG`（Tier 3）**：畫面 + log + 子行程樹 CPU 連續 ≥ 10 分鐘零變化（專門攔截測試或建置子行程死鎖）。讀取鑑識包中的 `process_tree` 葉節點 PID 與 `watched_logs` 尾端；屬安全可重跑的測試死鎖時向用戶確認（或依授權）終止卡死子 PID 並重跑，涉外部寫入則先上報用戶。
3. **自動休眠**：當 `watch` 輸出 `should_sleep: true`（無任何 `active` worker）時，立刻用 `manage_task{Action: "kill"}` 停掉 cron，避免空轉浪費資源。

---

## Common Mistakes

- **誤用 `herdr-core attach` 或輪詢 `orca check`**：`attach` 會把子終端控制序列透傳進外層造成誤報；Orca 輪詢 `check` 會吃掉信箱事件。監控一律走 `superagent.py watch`。
- **只看 `status == "working"` 以為沒卡住**：子行程死鎖時外層永遠顯示 `working`。務必把測試日誌路徑放進 `--watch-log` 或階段 `logs/`，讓 `watch` 同時核對畫面、log 與子行程樹 CPU。
- **給 `agy` 寫相對路徑**：`agy` 子代理可能不讀完整上下文而拼錯路徑觸發權限對話框。Brief 內所有檔案一律寫絕對路徑。
- **卡在權限對話框時直接 `send --force "y"`**：違反授權紀律。永遠先檢視原因，改 brief 邊界或交由用戶定奪。
- **審查超過 3 輪還一直打補丁**：第 3 輪不過代表 Brief 有結構性空白，必須熔斷重寫 Brief 並丟棄分支重做。
- **重做超過上限還繼續重派**：重做不是無限重試。`reset-stage` 回 `STAGE_HALTED` 就停，交 Owner 裁定；不要用 `stage-new --force` 或換階段名稱繞過計數。
- **沒釘 model／effort 就派工**：`dispatch` 對 `model` 或 `effort` 為空的角色回 `ROLE_UNPINNED`，因為留空會吃各 CLI 當下的預設，同一流程每次結果不同。先 `set-role` 補齊；確實要用 CLI 預設才加 `--allow-cli-default`。注意 `dispatch --cli` 覆寫 CLI 時仍沿用該角色的 `model`，換 CLI 時須同時給 `--model`。

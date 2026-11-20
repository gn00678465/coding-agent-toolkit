# 雙層卡死監控協議（Dual-Layer Watchdog Protocol）

本協議結合 `swarm_monitor` 的「狀態層停滯偵測」與 OS 層「靜默卡死偵測」，專門消滅「外層顯示 `working`、實際上子行程已死鎖數小時卻無人知曉」的盲點。

---

## 1. 為什麼需要雙層偵測？

| 盲點 | 單靠 `swarm_monitor` | `superagent` 雙層 Watchdog |
|---|---|---|
| Worker 忘記寫完成標記或回報漏掉對象 | 能抓到（全體 `waiting`） | **Layer 1（State Stall）** 抓到並 Tier 1 自動重喚一次 |
| Worker 卡在權限確認／信任對話框／額度耗盡 | 若仍顯示 `working` 會漏抓 | **Layer 2a（Interactive Block）** 掃描畫面特徵，2 分鐘即通報 |
| 背景測試或建置子行程死鎖（例：`cargo test` 單一執行檔卡死 1.5 小時） | 看到 `working` 視為正常長編譯而漏抓 | **Layer 2b（Silent Hang）** 同時比對「畫面 hash + 監控 log `(mtime, size)` + 子行程樹總 CPU 秒數」，三者連續 10 分鐘零變化立刻蒐證通報 |

---

## 2. 監控輸入訊號（每個活躍 Worker）

每次執行 `uv run <skill>/scripts/superagent.py watch --project <dir> [--auto-nudge] --output <out>`，對每個 `status == "active"` 的 worker 採集五組客觀證據：

1. **完成標記（Report Marker）**：檢查目標 `report_path` 是否存在，且檔案尾端 20 行（忽略空行）包含精確的 `expected_marker`（例如 `VERDICT: PASS`、`VERDICT: FAIL`、`IMPL DONE`）。
2. **後端生命週期狀態（Backend State）**：
   - `herdr`：`herdr-core get <addr>` 取得 `state`（`live`/`finished`）、`status.state`（`working`/`done`/`idle`/`waiting`）、`status.msg`、`turn`、`pid`、`foreground.pid`、`exit_code`。
   - `orca`：`orca orchestration status --json`（或對應 worker 查詢）取得 dispatch 狀態。
3. **終端畫面指紋與特徵（Screen Snapshot）**：
   - `herdr-core read --lines 45 <addr>` 去除動態雜訊列（如耗時秒數、token 進度條）後計算 `sha256`（`screen_hash`）。
   - 針對尾端 25 行比對互動／阻塞特徵正則（`INTERACTIVE_PATTERNS`）。
4. **日誌進度（Watched Logs）**：
   - 若登記了 `watch_logs`（或階段 `logs/` 目錄下最新修改檔案），記錄其 `(path, mtime, size)`。
5. **子行程樹 CPU 進度（OS Process Subtree）**：
   - 以 worker 根 PID（Windows 採 `Get-CimInstance Win32_Process` + `Get-Process`；POSIX 採 `ps`）展開全部後代行程，計算所有後代（排除外層閒置輪詢殼若可辨識，或整體加總）的 `total_cpu_sec`，並保留每個葉節點行程的 `pid`、`ppid`、`name`、`cmdline`、`created`、`cpu_sec`。

---

## 3. 互動／權限卡住特徵（`INTERACTIVE_PATTERNS`）

以下任一特徵出現在終端畫面尾端 25 行，且畫面指紋連續 ≥ `prompt_stall_sec`（預設 120 秒）無變化時，判定為 `INTERACTIVE_BLOCK`：

- 權限／確認提示：`Do you want to proceed`, `Allow once`, `Allow for this session`, `Approve`, `Permission required`, `\[y/N\]`, `\[Y/n\]`, `Press Enter to continue`
- 信任／登入提示：`Do you trust the files`, `trust this folder`, `Please login`, `Sign in`, `Enter password`, `passphrase`
- 額度／限流提示：`rate limit`, `quota exceeded`, `usage limit`, `overloaded`, `hit your limit`, `try again at`

> [!CAUTION]
> **硬性禁令**：Watchdog 與 Router **永遠不可**自動幫子 agent 按下權限對話框的確認鍵（遵守 `CLAUDE.local.md` 與 `dsh-superagent` 授權紀律）。偵測到 `INTERACTIVE_BLOCK` 時，只准記錄鑑識包並回報 Router 決定「關掉改 brief 重派」、「切換模型」或「請用戶確認」。

---

## 4. 分級處置矩陣

| 判定事件 | 條件 | 分級 | `watch` 動作 | Router 應對 |
|---|---|---|---|---|
| `READY_FOR_ROUTER` | 報告檔出現 `expected_marker` | Tier 0 | 標記 `ready`，清空卡死計數 | 跑 `verify-gate` → 讀報告 → 寫 `ruling` 或推進下一階段 |
| `WORKER_EXITED_NO_MARKER` | 後端回報 `state == "finished"` 但未出現 `expected_marker` | Tier 2 | 立即寫出鑑識包並通報 | 讀最後畫面與 exit code，補收尾或重派 |
| `INTERACTIVE_BLOCK` | 命中互動／權限／額度特徵且畫面停滯 ≥ `prompt_stall_sec`（預設 120s） | Tier 2 | 絕不代按；寫出鑑識包並通報 | 權限問題→關掉改 brief 重派或問用戶；額度問題→切模型／fallback CLI |
| `STATE_STALL` | Worker 為 `done`/`idle`/`waiting` 但缺 `expected_marker`，停滯 ≥ `state_stall_sec`（預設 180s） | Tier 1 | `--auto-nudge` 下第 1 次自動送一次催促訊息並記 `nudged_at`；若下輪仍停滯則升格 `ESCALATE_ROUTER` | 檢視 worker 畫面確認是否遺漏最後一步或卡在邏輯疑問 |
| `SILENT_HANG` | Worker 顯示 `working`，但 `screen_hash` + `watch_logs (mtime,size)` + `subtree total_cpu_sec` 皆無變化（CPU delta < `0.5s`）連續 ≥ `silent_hang_sec`（預設 600s） | Tier 3 | 寫出完整鑑識包（含全部子行程樹 PID／CommandLine／建立時間與 log 尾端）並通報 Router | Router 判斷根因：若為可安全重試的單一測試子行程死鎖，詢問用戶或依授權終止該子 PID 並重跑；若涉寫入／外部狀態，上報用戶決策 |
| `HEALTHY` | 畫面、log 或 CPU 任一有前進 | — | 重置 `stalled_since` 與 `alert_count` | 繼續等待下一個 cron tick |

---

## 5. 防重複告警與自動休眠（借鏡 `swarm_monitor`）

- **告警簽章（Signature）**：`<worker_id>:<incident_type>:<screen_hash[:12]>`
- **冷卻期（Cooldown）**：同一簽章在 `repeat_cooldown_sec`（預設 `600` 秒）內不重複通報（`suppressed_by_cooldown: true`）。
- **上限（Max Alerts）**：同一簽章累計告警達 `max_alerts`（預設 `3` 次）且狀態仍未改變時，標記 `muted: true`，不再重複打擾，直到畫面或狀態改變。
- **自動休眠（Dormancy）**：當所有註冊 worker 皆已 `closed` / `ready`，或連續 `dormant_idle_ticks`（預設 `5` 次，約 15 分鐘）無任何活躍 worker 時，`watch` 輸出 `should_sleep: true`，Router 立即 `manage_task{Action: "kill"}` 取消自己的 cron 排程。

---

## 6. 鑑識包格式（`watchdog/<worker>_incident_<ts>.json`）

```json
{
  "timestamp": "2026-11-19T09:30:00Z",
  "worker_id": "impl-01",
  "stage": "01-auth-refactor",
  "incident_type": "SILENT_HANG",
  "tier": 3,
  "stalled_seconds": 642,
  "backend": "herdr",
  "backend_ref": "t9s",
  "backend_status": {"state": "live", "agent_status": "working", "msg": "2 shells still running"},
  "screen_tail": ["...last 40 lines..."],
  "watched_logs": [{"path": "...", "mtime": "...", "size": 53625, "tail": ["...last 20 lines..."]}],
  "process_tree": [
    {"pid": 35192, "ppid": 9904, "name": "cargo.exe", "cpu_sec": 1.05, "cmdline": "..."},
    {"pid": 42252, "ppid": 35192, "name": "secrets-xxx.exe", "cpu_sec": 0.12, "cmdline": "..."}
  ],
  "recommended_action": "Inspect hung leaf process PID 42252; confirm safety before terminating or escalating to owner."
}
```

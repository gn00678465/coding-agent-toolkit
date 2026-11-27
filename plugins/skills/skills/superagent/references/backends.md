# 雙後端操作參考（`herdr-core` & Orca `orchestration`）

`superagent.py` 將派工（`dispatch`）、巡檢（`watch`）、深度鑑識（`diagnose`）、重喚（`nudge`）與清理（`close-worker`）抽象為雙後端介面，由 `.workflow/config.json` 的 `"backend"` 欄位決定（預設 `"herdr"`，可切換 `"orca"`）。

---

## 1. 後端 A：`herdr-core`（預設，推薦用於跨 CLI + 完整行程監控）

### 執行檔名稱解析
- Windows 上通常只有 `herdr-core`（無 `hc` 別名）；macOS/Linux 常用 `hc`。
- `superagent.py` 依序查找 `herdr-core` → `hc`，找到即用。

### 核心指令對照
| 動作 | 實際命令 | 備註 |
|---|---|---|
| 啟動背景 Worker | `herdr-core run --bg --name <name> --cwd <workdir> --label herdr.space=<space> --label herdr.tab=<name> <cli> <args...>` | 解析回傳 JSON 的 `address`（如 `t9s`）作為 `backend_ref` |
| 查詢狀態與 PID | `herdr-core get <addr>` | 回傳 `state`, `status.state`, `status.msg`, `pid`, `foreground.pid`, `turn`, `exit_code` |
| 讀取畫面（純文字） | `herdr-core read --lines 45 <addr>` | **嚴禁使用 `herdr-core attach`**（避免終端控制序列誤觸發外層通知） |
| Tier 1 自動重喚 | `herdr-core send <addr> "<nudge message>"` | 僅在 `STATE_STALL` 時呼叫一次，不加 `--force` 避免誤按權限對話框 |
| 結束與清理 | `herdr-core kill <addr>` → `herdr-core rm <addr>` | 階段完成或廢棄分支時執行 |

### 預設 CLI 啟動參數（可在 `.workflow/config.json` 覆寫）

每個角色的 `cli`（harness）、`model`、`effort` 都必須在 `roles` 明確設定；`dispatch` 遇到 `model` 或 `effort` 為空會拒絕（`ROLE_UNPINNED`）。三個 CLI 的 effort 旗標不同：

| CLI | model | effort |
|---|---|---|
| `claude` | `--model <id>` | `--effort <level>` |
| `codex` | `-m <id>` | `-c model_reasoning_effort="<level>"` |
| `agy` | `--model <id>` | `--effort <level>` |
| Orca `worker-start` | `--model <id>` | `--effort <level>` |

1. **Claude Code（`claude` — Brief / Implementor / Fixer）**：
   ```text
   claude --model opus --effort high --permission-mode auto "讀 <brief 絕對路徑> 並照做。"
   ```
   - 預設用 `--permission-mode auto`，不可擅自加 `--dangerously-skip-permissions`（除非用戶當次明確同意）。

2. **Codex（`codex` — Brief Review / Code Review）**：
   ```text
   codex --no-daemon -s workspace-write -c sandbox_workspace_write.network_access=true --add-dir <artifacts_dir> --add-dir <logs_dir> -m gpt-6.1-terra -c model_reasoning_effort="high" -a never "讀 <brief 絕對路徑> 並照做。"
   ```

3. **Antigravity（`agy` — Brief Review / Design & EGM Review）**：
   ```text
   agy --add-dir <artifacts_dir> --add-dir <logs_dir> --model <id> --effort <level> "讀 <brief 絕對路徑> 並照做。"
   ```
   - 若要跑 `egm-review`，可在 `config.json` 的 `cli.agy.extra_args` 設定 `-i "/egm-review ..."` 與額外 `--add-dir`。
   - **鐵律**：`brief` 內所有檔案一律寫絕對路徑，防止 `agy` 派出的子代理在工作區外觸發讀檔權限提示。

---

## 2. 後端 B：Orca `orchestration`（在 Orca 環境切換使用）

### 執行檔名稱解析
遵循 `orchestration` skill 規則：
1. 環境變數 `ORCA_CLI_COMMAND`（若有）
2. `ORCA_DEV_REPO_ROOT` 存在時用 `orca-dev`
3. Linux 非 Orca 終端用 `orca-ide`
4. 其餘使用 `orca`

### 核心指令對照
| 動作 | 實際命令 | 備註 |
|---|---|---|
| 啟動 Worker | `orca orchestration worker-start --spec "讀 <brief 絕對路徑> 並照做。" --worktree <current\|new-child> [--name <name>] --agent <claude\|codex\|...>` | 取得回執中的 `dispatch_id` 作為 `backend_ref`；切勿自行建 checkout，交由 `worker-start` 管理 |
| 查詢狀態 | `orca orchestration status --json` | 解析對應 `dispatch_id` 的狀態與停滯資訊 |
| 重喚／補充訊息 | `orca orchestration send --to dispatch:<dispatch_id> --subject "<topic>" --body "<message>"` | 遵循 `orchestration` 規範，不直接操作 worker 終端 |
| 回覆問題 | `orca orchestration reply --id <message_id> --body "<answer>"` | 屬於 Router 權限內直接回覆，涉及產品決策先問用戶 |

> [!NOTE]
> 使用 Orca 後端時，Orca 原生具備事件喚醒機制（絕不寫迴圈輪詢 `check` 吃掉信箱）；`superagent.py watch` 在 Orca 後端主要透過「目標 `report_path` 完成標記 + `watch_logs` 檔案 `mtime/size` 靜默檢查 + 唯讀狀態查詢」補足子行程靜默卡死偵測，不消費 Orca 訊息佇列。

---

## 3. `.workflow/config.json` 範例

```json
{
  "version": 1,
  "project_name": "my-project",
  "project_root": "D:/Projects/my-project",
  "backend": "herdr",
  "herdr_space": "my-project",
  "artifacts_dir": "D:/Projects/my-project/.workflow/stages",
  "logs_dir": "D:/Projects/my-project/.workflow/stages",
  "max_review_rounds": 3,
  "max_stage_resets": 2,
  "watchdog": {
    "poll_cron": "*/3 * * * *",
    "state_stall_sec": 180,
    "prompt_stall_sec": 120,
    "silent_hang_sec": 600,
    "cpu_delta_epsilon_sec": 0.5,
    "repeat_cooldown_sec": 600,
    "max_alerts": 3,
    "dormant_idle_ticks": 5
  },
  "roles": {
    "router": { "cli": "agy", "model": null, "effort": null },
    "brief": { "cli": "claude", "model": "opus", "effort": "high" },
    "brief-review": { "cli": "codex", "model": "gpt-6.1-terra", "effort": "high" },
    "impl": { "cli": "claude", "model": "opus", "effort": "high" },
    "fix": { "cli": "claude", "model": "opus", "effort": "high" },
    "review": { "cli": "codex", "model": "gpt-6.1-terra", "effort": "high" },
    "review-a": { "cli": "codex", "model": "gpt-6.1-terra", "effort": "high" },
    "review-b": { "cli": "codex", "model": "gpt-6.1-terra", "effort": "high" }
  }
}
```

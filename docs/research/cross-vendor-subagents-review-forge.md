# 研究筆記：跨廠商子代理（Claude Code ⇄ Codex）與 review-forge 多模型審查設計

- **主要來源**：
  - Claude Code 官方文件（2026-10-13 以 `curl https://code.claude.com/docs/en/<page>.md` 取得原始 Markdown）：[`sub-agents`](https://code.claude.com/docs/en/sub-agents)、[`plugins/components`](https://code.claude.com/docs/en/plugins/components)、[`plugins-reference`](https://code.claude.com/docs/en/plugins-reference)（現為 Plugin manifest reference）、[`plugins/install`](https://code.claude.com/docs/en/plugins/install)、[`plugins/loading`](https://code.claude.com/docs/en/plugins/loading)、[`plugins/org`](https://code.claude.com/docs/en/plugins/org)、[`settings`](https://code.claude.com/docs/en/settings)、[`settings-reference`](https://code.claude.com/docs/en/settings-reference)、[`skills`](https://code.claude.com/docs/en/skills)、[`cloud-environments`](https://code.claude.com/docs/en/cloud-environments)、[`headless`](https://code.claude.com/docs/en/headless)、[`cli-reference`](https://code.claude.com/docs/en/cli-reference)、[`mcp`](https://code.claude.com/docs/en/mcp)、[`tools-reference`](https://code.claude.com/docs/en/tools-reference)
  - 本機 `claude` CLI 2.1.296：`claude --help`、`claude agents --help`、`claude plugin --help`、`claude auth status --help`、`claude mcp serve --help`，以及在 scratchpad 內用 `--plugin-dir` 對一個自製探針 plugin 做的 `claude -p` 實測（見 1.1.4）
  - `openai/codex` 原始碼，`git clone --depth 1`，commit **`f82e36592278a0a782fb0d0fc97e5fa10e832ac2`**（2026-10-13）：`codex-rs/config/src/config_toml.rs`、`codex-rs/agent-roles/src/{agent_role_config,loader,discovery}.rs`、`codex-rs/core/src/agent/{role,role_tests,child_config}.rs`、`codex-rs/core-plugins/src/manifest.rs`、`codex-rs/exec/src/cli.rs`、`codex-rs/exec/src/lib.rs`、`codex-rs/utils/cli/src/shared_options.rs`、`codex-rs/cli/src/{main,login,mcp_cmd}.rs`、`codex-rs/config/src/loader/mod.rs`、`codex-rs/ext/skills/src/catalog_prompt.rs`、`codex-rs/skills/src/interface.rs`
  - Codex 官方文件：`developers.openai.com/codex/*` 現在以 308 轉址到 `learn.chatgpt.com/docs/*`，加 `.md` 取得原始 Markdown：[`agent-configuration/subagents`](https://learn.chatgpt.com/docs/agent-configuration/subagents.md)、[`non-interactive-mode`](https://learn.chatgpt.com/docs/non-interactive-mode.md)、[`mcp-server`](https://learn.chatgpt.com/docs/mcp-server.md)（移除公告）、[`sandboxing`](https://learn.chatgpt.com/docs/sandboxing.md)；外掛建置文件 [`developers.openai.com/plugins/build/plugins`](https://developers.openai.com/plugins/build/plugins.md)
  - `cursor/plugins` repo，`git clone --depth 1`，commit **`1dcc2bacde73ddd284803b7af28164d0436198fc`**（2026-10-12）：`pstack/skills/interrogate/SKILL.md`（與 `raw.githubusercontent.com/.../main/...` 版逐位元相同）、`pstack/skills/interrogate/references/*`、`pstack/skills/setup-pstack/SKILL.md`、`pstack/plugin.json`、`pstack/.cursor-plugin/plugin.json`
  - 本 repo：`plugins/advisor/agents/*.md`、`plugins/advisor/skills/orchestration/{SKILL.md,references/dispatch-and-flags.md,scripts/dispatch-codex.js,scripts/dispatch-claude-advisor.js}`、`plugins/code-review/skills/review-forge/**`、各 plugin 的 `.claude-plugin/` 與 `.codex-plugin/` manifest、`apm.yml`
- **檢索備註**：
  - 本筆記原本的題目是「專案層級 subagent 與 plugin 載入」，中途依使用者需求改為三個目標（cc 內呼叫 Codex 的 subagent、Codex 內呼叫 Claude 的 subagent、review-forge 多廠商化）。平台背景只保留這三個目標用得到的部分。
  - **本環境沒有安裝 `codex` 與 `grok` CLI**（`which codex grok` 無輸出），所以 Codex 端的行為只以原始碼與文件為準，**沒有實際執行過**。凡是 Codex 執行期的行為，文中都標成「依原始碼」或「未驗證」。
  - `gh api repos/openai/codex/...` 在此 session 回 403（repo 未掛載），所以沒能查 release tag 與 commit 歷史；Codex 原始碼結論只綁定在上面這個 main commit。
  - **Codex 文件與原始碼有出入**：文件說 custom agent 檔可以覆寫 `sandbox_mode`、`mcp_servers`，但 `f82e365` 的 `core/src/agent/role.rs` 會明確丟掉這兩個欄位（見 1.3.3）。本文以原始碼為準，並把文件說法並列出來。
  - **`codex mcp-server` 已經移除**（官方移除公告，且 `cli/src/main.rs` 已沒有這個子命令），所以「把 Codex 當 MCP server 給 Claude 用」這條路已經不能用了。
  - `apm.yml` 把 `pstack` 鎖在 `08bd59b…`，本文讀的是 `main`（`1dcc2ba`）。interrogate 在這裡只當參考，不受版本鎖影響。
- **檔案位置說明**：延續 `docs/research/` 的慣例（`skill-router.md`、`agents-md-refactoring.md`），本檔是第四篇研究筆記。

---

## 1. 平台背景（只保留三個目標需要的部分）

### 1.1 Claude Code subagent

#### 1.1.1 定義位置與優先序

名稱相同時，優先序較高的位置勝出（來源：`code.claude.com/docs/en/sub-agents` 的「Choose the subagent scope」一節）：

| 位置 | 範圍 | 優先序 |
|---|---|---|
| Managed settings（`<managed dir>/.claude/agents/`） | 整個組織 | 1（最高） |
| `--agents '<json>'` CLI 旗標（在 `-p` 模式下也可以給 JSON 檔路徑，需 v2.1.281+） | 當次 session | 2 |
| `.claude/agents/`（從 cwd 往上找到 repo root，離 cwd 最近的勝出） | 專案 | 3 |
| `~/.claude/agents/` | 使用者 | 4 |
| Plugin 的 `agents/` | plugin 啟用的範圍 | 5（最低） |

- 專案與使用者範圍會遞迴掃描子資料夾，但身分只看 frontmatter 的 `name`。Plugin 的子資料夾則會成為名稱的一部分：`agents/review/security.md` 會註冊成 `my-plugin:review:security`（來源：同頁）。
- `name` 不能包含 `:`，因為冒號保留給 plugin 的 scoped 名稱（來源：同頁 frontmatter 表）。
- **`claude agents` 不是列出 subagent 的指令**：在 2.1.296 中它是「Manage background agents」（`claude agents --help`），列的是背景 session。

#### 1.1.2 Frontmatter（只列跨廠商 lane 會用到的欄位）

來源：`sub-agents` 的 Frontmatter reference。只有 `name` 與 `description` 是必填，其他未知欄位會被**靜默忽略**。

| 欄位 | 對跨廠商 lane 的意義 |
|---|---|
| `tools` / `disallowedTools` | lane 只需要 `Bash, Read, Grep, Glob`。**不要列 `Agent`**，否則 lane 自己也能再派 subagent（列出 `Agent` 才能 spawn）。 |
| `model` | 外層包裝用的 Claude 模型（`sonnet`/`opus`/`haiku`/`fable`/完整 ID/`inherit`）。它只負責驅動 CLI，可以選便宜的模型。注意 `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` 會忽略這個欄位。 |
| `skills` | 啟動時預載**完整**的 skill 內容（最多 32 個）。可以引用 plugin skill（實測見 1.1.4）。 |
| `mcpServers` | 子代理專屬的 MCP。**plugin agent 會忽略這個欄位。** |
| `permissionMode` / `hooks` / `initialPrompt` | **plugin agent 會忽略。** |
| `maxTurns`、`effort`、`background`、`isolation: worktree`、`omitClaudeMd` | 都可用（plugin agent 也支援）。`omitClaudeMd: true` 適合「所有資訊都由委派訊息提供」的 lane。 |

Plugin agent 支援的欄位為 `name, description, model, effort, maxTurns, tools, disallowedTools, skills, memory, background, omitClaudeMd, isolation, color, experimental.cacheTtl`；`permissionMode, hooks, mcpServers, initialPrompt` 會被忽略（來源：`code.claude.com/docs/en/plugins/components` 的「Frontmatter fields in plugin agents」）。

#### 1.1.3 Plugin agent 的路徑變數

`${CLAUDE_PLUGIN_ROOT}` 寫在 skill、command、**agent 的 Markdown 內文**中會被就地替換。它**不會**出現在 Bash 工具的環境變數裡（來源：`plugins-reference` 的「Where each variable resolves」表與其後說明）。所以 `plugins/advisor/agents/codex-implementer.md` 內文寫的 `node "${CLAUDE_PLUGIN_ROOT}/skills/orchestration/scripts/dispatch-codex.js"` 是正確用法。它的「`CLAUDE_PLUGIN_ROOT` 未設定時用 Glob 找」備援，只有在 agent 被複製到 `.claude/agents/` 時才派得上用場。

> 未驗證：project-level agent（`.claude/agents/*.md`）內文中的 `${CLAUDE_PROJECT_DIR}` 是否也會被替換。文件只列出 plugin 元件的替換規則。

#### 1.1.4 subagent 使用 plugin 的 skill 與 MCP（2.1.296 實測）

文件只寫了 `skills` 欄位「draws from the same set of skills Claude can invoke」，沒有寫能不能用 `plugin:skill` 名稱。所以我在 scratchpad 建了一個 plugin `probe`，內含一個 skill `secret-word`（內容只有一個暗號）、一個 MCP server `tok`（回傳固定字串），再用 `claude -p --plugin-dir <probe> --model haiku` 測試。每個 subagent 都只給 `tools: Read`，並要求它「不呼叫工具，直接回報預載內容」：

| subagent | 定義位置 | frontmatter | 結果 |
|---|---|---|---|
| `proj-agent` | `.claude/agents/` | `skills: [probe:secret-word]` | 回報暗號（**預載成功**） |
| `probe:plug-agent` | plugin `agents/` | `skills: [probe:secret-word]` | 回報暗號 |
| `bare-agent` | `.claude/agents/` | `skills: [secret-word]`（不加 namespace） | 回報暗號（沒有同名衝突時，短名稱也能解析） |
| `ctrl-agent` | `.claude/agents/` | 無 `skills` | `NONE`（對照組） |
| `mcp-agent` | `.claude/agents/` | `tools: mcp__plugin_probe_tok__get_token` | 沒有 `--allowedTools` 時被權限拒絕；加上 `--allowedTools=mcp__plugin_probe_tok__get_token` 後回傳 MCP 結果 |

結論：

1. **project-level subagent 可以用 `plugin:skill` 名稱預載 plugin skill。** 建議永遠寫成 namespaced 形式，避免同名衝突。
2. **project-level subagent 可以把 plugin 的 MCP 工具放進 `tools` 白名單。** 工具名稱格式是 `mcp__plugin_<plugin>_<server>__<tool>`（來源：`plugins/components` 的「Server names, tool names, and reloads」）。在 `-p` 模式下仍需要 `--allowedTools` 或 `permissions.allow`。
3. 未驗證：在 `mcpServers:` 中以字串 `"plugin:probe:tok"` 引用 plugin server。plugin agent 本身也不能用 `mcpServers`，所以 plugin 應該把 MCP 放在 plugin 的 `.mcp.json`。

### 1.2 讓 plugin 隨專案自動載入（含雲端限制）

```json
// .claude/settings.json（commit 進 repo）
{
  "extraKnownMarketplaces": {
    "coding-agent-toolkit": {
      "source": { "source": "github", "repo": "gn00678465/coding-agent-toolkit" }
    }
  },
  "enabledPlugins": {
    "code-review@coding-agent-toolkit": true,
    "advisor@coding-agent-toolkit": true
  }
}
```

- `extraKnownMarketplaces` 只在協作者對該資料夾**接受 workspace trust 對話框之後**才生效。未信任時會被無訊息忽略。在 `-p` 模式下，則只有在使用者過去已經互動式信任過（或 `~/.claude.json` 有 `hasTrustDialogAccepted`）時才生效（來源：`plugins/org` 的「Require plugins per repository」、`settings-reference` 的 `extraKnownMarketplaces`）。
- **相對路徑來源的 plugin**（本 repo 自家的 `./plugins/advisor`、`./plugins/code-review` 都是）在 marketplace 生效後，會直接從 marketplace 副本載入。**外部來源**（本 repo 的 `web-quality-skills`、`pstack` 等 url 來源）只寫在專案 settings 不會自動安裝，每位協作者要自己跑 `claude plugin install <name>@<marketplace> --scope project`（來源：`plugins/org` 同節、`plugins/loading` 的「Enabled in project settings but not installed」）。
- **雲端 session（claude.ai/code）**：repo `.claude/settings.json` 宣告的 `enabledPlugins` 與 `extraKnownMarketplaces` **都不會安裝**。原因是加入 marketplace 需要 trust 對話框，而雲端 session 從不顯示這個對話框。只有組織的 **server-managed settings** 能讓雲端 session 安裝 plugin，而且 session 會等這些設定抵達後才安裝（來源：`cloud-environments` 的「What carries over from your setup」表、`plugins/loading` 的「Plugins shared through a repository」、`plugins/org` 的「When each surface applies the plugin keys」表）。
  - 但 repo 內的 `.claude/agents/`、`.claude/skills/`、`.mcp.json`（單一 repo session）**會**帶過去，因為它們是 clone 的一部分（同表）。所以**要讓雲端 session 也能用跨廠商 lane，agent 檔得放在 `.claude/agents/`，不能只靠 plugin。** 此外雲端映像不一定有 `codex` CLI（本 session 就沒有），lane 必須能回報 `unavailable`。

### 1.3 Codex custom agent（「角色」）

#### 1.3.1 位置與載入順序（依原始碼）

- 每個設定層（user `~/.codex/`、專案 `.codex/` 等）都可以用兩種方式提供 role（`agent-roles/src/loader.rs`）：
  1. 在 `config.toml` 中寫 `[agents.<name>]`，欄位為 `description`、`config_file`、`nickname_candidates`（`config/src/config_toml.rs` 的 `AgentRoleToml`，`deny_unknown_fields`）。
  2. 把 `<config_folder>/agents/**/*.toml` 遞迴自動探索（`agent-roles/src/discovery.rs` 只收 `.toml`）。
- 同一層內名稱重複時，會跳過並產生 startup warning。跨層時，**高層覆蓋低層**；高層缺的 `description`、`config_file` 等欄位會從低層補（`merge_missing_role_fields`）。
- **專案層要 trust 才載入**：`config/src/loader/mod.rs` 的註解寫明 `tree`、`repo` 兩層的 `.codex/config.toml` 是「loaded but disabled when untrusted」，而 `load_agent_roles` 走的 `layers_low_to_high()` 會濾掉 disabled 層（`config/src/state.rs`）。所以未信任專案的 `.codex/agents/` 也不會載入（這是依程式碼的推論，沒有實際執行）。文件也寫「Codex loads project `.codex/config.toml` only for trusted projects」（`developers.openai.com/plugins/build/plugins`）。
- 內建 role 有 `default`、`worker`、`explorer`（`core/src/agent/role.rs` 的 `built_in::configs()`）。同名的自訂 role 會優先（文件）。

#### 1.3.2 Role 檔 schema

`RawAgentRoleFileToml` = `name`、`description`、`nickname_candidates`，再加上整份 `ConfigToml`（flatten，`deny_unknown_fields`），見 `agent-roles/src/agent_role_config.rs`。自動探索到的檔案**必須**有 `name`、`description`、非空的 `developer_instructions`；`name` 才是真正的身分，檔名不算（文件與原始碼一致）。

#### 1.3.3 哪些欄位真的會套用到子代理（文件與原始碼不一致）

`core/src/agent/role.rs` 的 `apply_role_to_config_inner` 只取 `AgentRoleOverrides`。檔頭註解寫：「Roles may customize the child or reduce its capabilities, but never replace the parent session's authority」。

| 欄位 | f82e365 實際行為 |
|---|---|
| `developer_instructions`、`model`、`model_reasoning_effort`、`model_reasoning_summary`、`model_verbosity`、`personality`、`service_tier` | 套用 |
| `[features]` | **只有關閉**有效，而且只限 `shell_tool`、`apps`、`plugins`、`memory_tool`、`request_permissions_tool`。打開會被忽略。 |
| `skills`（`[[skills.config]]` 等） | **只有停用**有效（`enabled = false`、`include_instructions = false`）。 |
| `sandbox_mode`、`sandbox_workspace_write`、`approval_policy`、`mcp_servers`、`model_provider`、`openai_base_url`、`notify`、`apps` | **不套用**。`role_tests.rs` 的 `apply_role_cannot_expand_parent_authority` 斷言「role must not control `sandbox_mode` / `mcp_servers` / …」；`apply_role_preserves_parent_sandbox_permissions` 斷言子代理的 permissions 等於父代理。 |

相對地，官方文件 `learn.chatgpt.com/docs/agent-configuration/subagents` 寫：「You can also include other supported `config.toml` keys in a custom agent file, such as `model`, `model_reasoning_effort`, `sandbox_mode`, `mcp_servers`, and `skills.config`」，範例中也有 `sandbox_mode = "read-only"` 與 `[mcp_servers.*]`。同一頁也寫了「Subagents inherit your current sandbox policy」，以及 CLI 會「reapplies the parent turn's live runtime overrides … even if the selected custom agent file sets different defaults」。

**實務結論**：在目前的 main 上，**不要依賴 role 檔設定 sandbox 或 MCP**。子代理一律繼承父 session 的 sandbox、approval、MCP、plugin。`child_config.rs` 的 `build_agent_shared_config` 會複製父 config，並以 `apply_spawn_agent_runtime_overrides` 套用 turn 的 approval、permission profile、cwd。Role 只能「改模型」或「縮減能力」。若 role 設了 `model` / `model_reasoning_effort`，spawn 工具描述會告訴模型「cannot be changed」（`spawn_tool_spec::format_role`）。

#### 1.3.4 子代理使用 plugin skill 與 MCP

子代理的 config 是父 config 的 clone，所以**父 session 已啟用的 plugin skill 與 MCP，子代理預設都能用**。role 只能用 `[features] plugins = false` 整個關掉（受 managed 要求約束，見 `apply_role_disables_plugins_unless_required_by_managed_policy` 測試），或用 `[[skills.config]] … enabled = false` 停用個別 skill（`apply_role_skills_config_disables_skill_for_spawned_agent` 測試）。Codex **沒有**「預載 skill 內容」這類欄位（Claude 的 `skills:` 沒有對應物）。

#### 1.3.5 spawn 工具

`core/src/tools/handlers/multi_agents_spec.rs`：`spawn_agent` 的參數有 `message` / `items`、`agent_type`、`fork_context`、`model`、`reasoning_effort`（V2 另有 `task_name`）；其他工具還有 `send_input`、`wait_agent`、`list_agents`、`close_agent` 等。全域設定放在 `[agents]`：`enabled`、`max_concurrent_threads_per_session`（舊名 `max_threads`）、`max_depth`、`default_subagent_model`、`default_subagent_reasoning_effort`、`interrupt_message`（`AgentsToml`）。

### 1.4 Codex plugin

- Manifest 搜尋順序：先找根目錄的 `plugin.json`，但它必須宣告 Agent Plugins `$schema` 才算數；否則依序找 `.codex-plugin/plugin.json` → `.claude-plugin/plugin.json` → `.cursor-plugin/plugin.json`（`utils/plugins/src/plugin_namespace.rs` 的 `find_plugin_manifest_path`、`exec-server-protocol/src/protocol.rs` 的 `DISCOVERABLE_PLUGIN_MANIFEST_PATHS`）。本 repo 的 `plugins/code-review/plugin.json` 沒有 `$schema`，所以會落到 `.codex-plugin/plugin.json`，這符合預期。
- **Codex plugin manifest 沒有 `agents` 欄位**：`core-plugins/src/manifest.rs` 的 `RawPluginManifest` 只有 `name, version, description, keywords, skills, mcpServers, apps, hooks, interface, extensions`，另有 `commands`。所以 **Codex plugin 無法發佈 custom agent**。skill 內的 `agents/openai.yaml` 只是 skill metadata（`interface`、`dependencies`、`policy.allow_implicit_invocation`，見 `skills/src/interface.rs`、`ext/skills/src/loader/metadata.rs`），不是 subagent 定義。
- 專案啟用 plugin：repo 的 `.agents/plugins/marketplace.json` 讓 plugin 可被發現，再在 `.codex/config.toml` 寫 `[plugins."<plugin>@<marketplace>"] enabled = true`。同樣要 trust（來源：`developers.openai.com/plugins/build/plugins` 的「Enable or disable a plugin for a repo」；`config/src/types.rs` 的 `PluginConfig { enabled, mcp_servers }`）。
- Codex 指示模型：SKILL.md 中的相對路徑（如 `scripts/foo.py`）要相對於該 SKILL.md 所在目錄解析（`ext/skills/src/catalog_prompt.rs:29`）。所以 Codex plugin 的 skill 可以直接寫 `node scripts/dispatch-claude.js`，不需要 `${CLAUDE_SKILL_DIR}`。

---

## 2. 目標一：在 Claude Code 中建立呼叫 Codex 的 subagent

### 2.1 呼叫方式：只剩 `codex exec`

| 方式 | 狀態 |
|---|---|
| `codex exec`（非互動） | **建議**。stdout 只輸出最終訊息，進度寫到 stderr（`non-interactive-mode`）。 |
| `codex review`（或 `codex exec review`） | 非互動程式碼審查，有 `--uncommitted`、`--base <branch>`、`--commit <sha>`、`[PROMPT]`（`exec/src/cli.rs` 的 `ReviewArgs`、`cli/src/main.rs` 的 `Review`）。輸出格式是 Codex 自己的，不是 review-forge 的模板，所以 review-forge 用 `codex exec` 加自訂 prompt 比較好控制。 |
| `codex mcp-server` | **已移除**。「The `codex mcp-server` command and the standalone `codex-mcp-server` binary have been removed」（[`learn.chatgpt.com/docs/mcp-server.md`](https://learn.chatgpt.com/docs/mcp-server.md)）。`cli/src/main.rs` 也沒有這個子命令，`codex mcp` 只剩 `list/get/add/remove/login/logout`（`cli/src/mcp_cmd.rs`）。 |
| `codex app-server` | JSON-RPC（不是 MCP），文件標示為 experimental、不支援正式環境。不建議拿來做 lane。 |

### 2.2 `codex exec` 旗標（依 `f82e365` 原始碼）

| 需求 | 旗標 | 來源 |
|---|---|---|
| prompt 從 stdin 讀取 | 位置參數 `-`（或省略）。若 stdin 是 pipe 又給了 prompt，stdin 會附加成 `<stdin>` 區塊 | `exec/src/cli.rs` |
| 模型 | `-m, --model <slug>` | `utils/cli/src/shared_options.rs` |
| 推理強度 | `-c model_reasoning_effort=high`（通用的 `-c key=value` 覆寫） | `utils/cli/src/config_override.rs` |
| Sandbox | `-s, --sandbox read-only\|workspace-write\|danger-full-access`。**`exec` 預設 read-only**（文件），且 headless 預設 `approval_policy = never`（`exec/src/lib.rs:591`） | 同上 |
| 工作目錄 | `-C, --cd <DIR>`，另有 `--add-dir`、`--worktree` | 同上 |
| 非 git 目錄 | `--skip-git-repo-check` | `exec/src/cli.rs` |
| 最終訊息寫檔 | `-o, --output-last-message <FILE>` | 同上 |
| 結構化輸出 | `--output-schema <FILE>`（JSON Schema） | 同上；`non-interactive-mode` |
| 事件串流 | `--json`：JSONL 事件 `thread.started` / `turn.started` / `turn.completed`（含 `usage`）/ `turn.failed` / `item.*` / `error` | `exec/src/exec_events.rs` |
| 不留 rollout | `--ephemeral` | `exec/src/cli.rs` |
| 可重現環境 | `--ignore-user-config`、`--ignore-rules`、`--strict-config` | 同上 |
| 續跑 | `codex exec resume <id>\|--last` | 同上 |
| 注意 | `-p` 在 Codex 是 **`--profile`**，不是 prompt | `shared_options.rs` |

**認證與 preflight**：`codex login status` 已登入時 exit 0，失敗時 exit 1（`cli/src/login.rs`）。CI 可以只對那一次呼叫設 `CODEX_API_KEY=…`（文件不建議設成 job 層級的環境變數）。

**逾時**：`codex exec` 沒有內建 wall-clock 逾時旗標（`exec/src/cli.rs` 沒有，屬未驗證的否定結論），所以要由外層強制。Claude 的 Bash 工具前景預設 2 分鐘、上限 10 分鐘（`BASH_DEFAULT_TIMEOUT_MS`、`BASH_MAX_TIMEOUT_MS`，見 `tools-reference`）。lane 的 dispatcher 截止時間要小於這個上限，或改用背景執行。

### 2.3 輸入與輸出 contract（建議）

- **輸入**：一律寫進 `mktemp` 產生的 spec 檔，再經 stdin 傳入並**關閉 stdin**。advisor 的 dispatcher 已經證明：繼承來的 pipe 不關閉，`codex exec` 會一直等 EOF。
- **輸出**：審查 lane 加上 `--output-schema findings.schema.json -o <tmp>.json`，由包裝 agent 讀 JSON 後套用 review-forge 模板寫成 `.review/<feature>/<model>.md`。在 read-only sandbox 中，Codex 本身不能寫 `.review/`。
  - 未驗證：`--output-schema` 是否要求 OpenAI strict 格式（所有屬性都列在 `required`、`additionalProperties: false`）。為求保險，schema 寫成 strict 相容。
- **用量**：要記錄成本時，再加 `--json` 讀取 `turn.completed.usage`。

### 2.4 可直接複製的 subagent 檔：`.claude/agents/codex-implementer.md`

這個 subagent 是**薄包裝**：它本身不寫程式也不審查，只負責把任務交給 `codex exec`、監看執行、核對結果，並以固定格式回報。下面每個旗標都對過 2.2 的原始碼表；`claude` 這一側的行為則以 2.1.296 文件為準。

````markdown
---
name: codex-implementer
description: Cross-vendor implementation lane that runs OpenAI Codex non-interactively (`codex exec`, workspace-write sandbox). Delegate here when you want a non-Anthropic model to implement a well-specified change. The caller must pass a complete spec (objective, files, interfaces, constraints, verification command). This agent never writes code itself; it drives codex, re-runs the verification, and returns a CODEX REPORT. If the codex CLI is missing or logged out, it returns STATUS unavailable instead of doing the work.
model: sonnet
tools: Bash, Read, Grep, Glob
maxTurns: 25
omitClaudeMd: true
---

# Codex implementer (thin wrapper)

You are a dispatcher and verifier. **OpenAI Codex writes the code, not you.**
Do not edit files, do not "finish" codex's work, and do not substitute your own
implementation when codex fails. A cross-vendor lane that silently becomes a
Claude lane defeats its purpose. Never spawn other agents.

## 1. Preflight (always first)

Run:

```bash
command -v codex && codex --version && codex login status
```

`codex login status` exits 0 when logged in and 1 when not. If any part fails,
stop and return the report in section 6 with `STATUS: unavailable` and the exact
stderr in `REASON`.

## 2. Prepare the run directory and the spec

Use a fresh directory per run, never a fixed path, so parallel lanes cannot
collide:

```bash
RUN=$(mktemp -d "${TMPDIR:-/tmp}/codex-lane.XXXXXX")
git rev-parse HEAD > "$RUN/pre-head.txt" 2>/dev/null
git status --porcelain > "$RUN/pre-status.txt" 2>/dev/null
cat > "$RUN/spec.md" <<'SPEC_EOF'
<restate the caller's spec here verbatim: Objective, Files, Interfaces,
Constraints, Verification command. List missing parts as explicit
"OPEN QUESTION:" lines. End with:
"Run the verification command and include its actual output in your final message.">
SPEC_EOF
echo "$RUN"
```

Use a quoted heredoc delimiter (`'SPEC_EOF'`) so the shell expands nothing in the spec.

## 3. Invoke codex

Make one Bash call and set the Bash tool `timeout` parameter to 660000 ms, so
the outer limit sits above the 600 s deadline below:

```bash
TO=$(command -v timeout || command -v gtimeout)
${TO:+$TO --kill-after=15s 600s} codex exec \
  --model "${CODEX_MODEL:-gpt-5.6-sol}" \
  -c model_reasoning_effort="${CODEX_EFFORT:-high}" \
  --sandbox workspace-write \
  --cd "$PWD" \
  --ephemeral \
  --json \
  --output-last-message "$RUN/final.md" \
  - < "$RUN/spec.md" > "$RUN/events.jsonl" 2> "$RUN/stderr.log"
echo "exit=$?"
```

Flag rationale:

- `-` with `< "$RUN/spec.md"`: the prompt comes from a file, so stdin hits EOF.
  Never pipe from a process that stays open, because codex waits on stdin until EOF.
- `--sandbox workspace-write`: codex may edit inside the workspace, with no
  network by default. Never use `danger-full-access`.
- `-c model_reasoning_effort=...`: the value is parsed as TOML and otherwise
  used as a literal string. Allowed levels depend on the model.
- `--ephemeral`: do not persist a rollout file.
- `--json`: stdout becomes JSONL events, so `turn.completed.usage` can be
  reported. `--output-last-message` still receives the final message.
- Add `--skip-git-repo-check` only if the caller says the directory is not a git repo.
- Use the model and effort the spec names; otherwise keep the defaults shown above.

Interpret the exit code:

- `exit=0`: codex completed.
- `exit=124` or `137` while `timeout` was present: the deadline was hit → `STATUS: timeout`.
- `exit=127`: the codex binary was not found → `STATUS: unavailable`. Preflight should already have caught this.
- Any other non-zero code: codex failed → `STATUS: invocation_error`. Quote the
  last 20 lines of `$RUN/stderr.log` and any `turn.failed` or `error` event from
  `$RUN/events.jsonl`.
- If neither `timeout` nor `gtimeout` exists, no deadline was enforced. Say so
  in `GAPS`. A Bash tool timeout moves the command to the background instead
  of killing it.

## 4. Verify independently

- `git status --porcelain` and `git diff --stat`, compared with `$RUN/pre-status.txt`.
  Attribute only the new changes to codex.
- Re-run the spec's verification command yourself and keep its real output.
- Read `$RUN/final.md`. Codex saying the change works is not evidence; your re-run is.
- Usage: `grep '"type":"turn.completed"' "$RUN/events.jsonl" | tail -1`.

If codex's changes are wrong, report the failing output. Do not patch them.

## 5. Rules

- One `codex exec` per task unless the caller decomposed the work.
- Never print or forward secrets. The spec text goes verbatim to a third-party model.
- If the spec turns out to be wrong (an architectural problem), stop and report.
  Fix decisions belong to the caller.
- Long wall time with near-zero local CPU is normal (codex reasons remotely).
  Do not kill the run for that.

## 6. Output format (return exactly this, nothing else)

```
CODEX REPORT
STATUS: complete | partial | timeout | invocation_error | unavailable
MODEL: <slug passed to --model>  EFFORT: <effort>  SANDBOX: workspace-write
EXIT: <exit code>  RUN_DIR: <$RUN>
OBJECTIVE: <one line>
CHANGES:
- <file> — <one-line summary from the actual diff>
VERIFIED: <command you re-ran> → <pass|fail>
<last ≤15 lines of its real output>
CODEX SAID: <one-line summary of $RUN/final.md; note any disagreement with the diff>
USAGE: <input_tokens/output_tokens from turn.completed, or "n/a">
GAPS: <open questions, missing deadline, unfinished items, or "none">
REASON: <only for timeout/invocation_error/unavailable: exact stderr tail>
```
````

**審查版（`codex-reviewer.md`）的差異**：

- `description` 改成「read-only review lane…」。
- 第 3 步改成 `--sandbox read-only`，並加上 `--output-schema "$RUN/schema.json"`。schema 在第 2 步用 heredoc 寫入（內容見 5.4 的 `findings.schema.json`）。
- 拿掉第 4 步的 git diff 與驗證。
- 第 6 步改成回傳 `CODEX REVIEW` 標頭，加上 `$RUN/final.md` 的原始 JSON，**不做任何編輯或排序**。
- 由 parent（review-forge）把 JSON 套用模板寫成 `.review/<feature>/<model>.md`。

**放在 plugin 時**（`plugins/<p>/agents/codex-implementer.md`）：內文可以直接寫 `${CLAUDE_PLUGIN_ROOT}`，會就地替換（1.1.3）。但 inline 的 `codex exec` 不需要任何 plugin 檔案，所以同一份檔案可以原封不動地放進 project `.claude/agents/`，雲端 session 也能用（1.2）。agent 名稱會變成 `<p>:codex-implementer`；frontmatter 只用到 plugin agent 支援的欄位（1.1.2），不需要修改。

**權限**：Bash 呼叫仍受 session 權限約束。要免確認，可以在 `.claude/settings.json` 加 `permissions.allow`，例如 `"Bash(codex exec *)"`，或在 auto mode 下執行。這條規則能否匹配多行指令與 `${TO:+…}` 前綴屬**未驗證**；比較穩的做法是把第 3 步包成一支 repo 腳本（如 `tools/codex-lane.sh`），再 allow 那支腳本。

### 2.5 相對 `plugins/advisor/agents/codex-implementer.md` 要改什麼

| 現行做法（prior art） | 問題 | 改法 |
|---|---|---|
| 強制經由 `${CLAUDE_PLUGIN_ROOT}/skills/orchestration/scripts/dispatch-codex.js`，並寫明「never hand-construct a `codex exec` command」 | 檔案放到 `.claude/agents/` 就沒有 plugin root；Glob 備援也要求 repo 中有那支腳本 | 改成上面的 **inline 指令**。stdin hang 的根因是「繼承到一條不會關閉的 pipe」，`- < file` 的檔案重導向在 EOF 時自然結束，可以避免。若要保留 dispatcher 的 process-tree kill 與 `--pidfile`，就把腳本複製到 repo 的 `tools/`，agent 檔改以 repo 相對路徑呼叫 |
| `-c model_reasoning_effort=high` 寫死在 dispatcher | 換模型時，該模型可能不支援 `high` | 改成 `${CODEX_EFFORT:-high}`，由 spec 指定 |
| `--output-last-message` 寫到 `os.tmpdir()/codex-final-<pid>-<ts>.txt` | 與 spec 檔、stderr 分散，事後追查困難 | 每次執行一個 `RUN=$(mktemp -d)`，裡面放 spec、final、events、stderr、pre-status |
| 沒有 `--ephemeral`、沒有 `--json` | 每次執行都留下 rollout；也無法回報用量 | 加上 `--ephemeral --json`，並在報告輸出 `USAGE` |
| 執行前沒有快照 | 無法區分 codex 的修改與先前就存在的未提交修改 | 先記錄 `pre-status.txt` 與 `pre-head.txt` |
| 報告沒有 `MODEL/EFFORT/EXIT/RUN_DIR/REASON` 欄位 | parent 無法機器判讀，也無法判斷是否為 stand-in | 補上（見第 6 節格式） |
| 逾時靠 dispatcher 的程序內 deadline | inline 版改用 `timeout`/`gtimeout`；macOS 預設沒有這兩個指令 | 沒有時在 `GAPS` 標明「no deadline」；需要跨平台硬性逾時就保留 dispatcher |
| 其餘部分：preflight、不靜默替代、自行重跑驗證、不派 agent、`tools: Bash, Read, Grep, Glob` | — | **全部保留**，它們正是這個 lane 的價值所在 |

---

## 3. 目標二：在 Codex 中建立呼叫 Claude Code 的 subagent

### 3.1 呼叫方式

| 方式 | 狀態 |
|---|---|
| `claude -p`（headless） | **建議**。exit 0 代表成功；執行中失敗（例如未認證）時，結果仍會印到 stdout（`headless` 的「Basic usage」）。 |
| `claude mcp serve` | 只「exposes Claude Code's tools to your MCP client」，也就是只開放 Read/Edit/Bash 這類工具，**不是**代理迴圈；工具確認也由客戶端負責（`mcp` 的「Use Claude Code as an MCP server」）。用它無法讓 Claude 模型來審查。 |

### 3.2 `claude -p` 旗標

依 `code.claude.com/docs/en/cli-reference` 與 `headless`：

| 需求 | 旗標 |
|---|---|
| 輸出 | `--output-format json`（`result`、`session_id`、`total_cost_usd`、`usage`、`modelUsage`）；加上 `--json-schema '<schema>'` 時，結構化結果會放在 `structured_output`；串流用 `stream-json` |
| 模型 | `--model opus\|sonnet\|haiku\|fable\|<完整 ID>`、`--fallback-model <清單>`、`--effort low…max` |
| 權限 | `--permission-mode dontAsk`（會被提示的全部拒絕，只放行規則允許的）、`--tools "Read,Grep,Glob"`（**限制**可用工具）、`--allowedTools`（只做**免確認**，不限制可用工具）、`--permission-prompts none`（v2.1.259+） |
| 上限 | `--max-turns N`、`--max-budget-usd X`（成本估計值，含 subagent） |
| 系統提示 | `--system-prompt(-file)` 取代、`--append-system-prompt(-file)` 附加 |
| 可重現性 | `--bare`：不載入 hooks/skills/plugins/MCP/CLAUDE.md，且**只認 `ANTHROPIC_API_KEY`**，不讀 OAuth。另有 `--no-session-persistence`、`--setting-sources`、`--strict-mcp-config` |
| 多目錄 | `--add-dir` |

重點：

- 不設 permission mode 時，`-p` 用的是「built-in starting permission mode, which can be `auto`」（`headless` 的「Auto-approve tools」）。所以審查 lane 要**明確**傳 `--permission-mode dontAsk --tools "Read,Grep,Glob"`。
- **沒有 `--bare` 的 `-p` 會執行專案 `.claude/settings.json` 的 hooks，並連接 `.mcp.json`，即使資料夾從未被信任**（`headless` 的「Start faster with bare mode」）。從 Codex 呼叫不受信任的 repo 時，要考慮 `--bare` 或 `--setting-sources user`。
- 認證檢查：`claude auth status` 已登入 exit 0、未登入 exit 1（`cli-reference`）。

### 3.3 Codex 端的 sandbox 與網路

子代理繼承父 sandbox（1.3.3）。`sandbox_workspace_write.network_access` 預設是 `false`（`config/src/types.rs` 的 `#[serde(default)] network_access: bool`），read-only 也無網路（`sandboxing` 文件）。`claude -p` 需要連到 Anthropic API，也要寫 `~/.claude`，所以在 Codex sandbox 中直接跑 `claude -p`，預期會被網路或寫入限制擋下（**未驗證**，本環境沒有 codex）。可行的做法：

1. 父 session 設 `[sandbox_workspace_write] network_access = true`，lane 加 `--no-session-persistence`。是否還需要寫 `~/.claude` 屬未驗證。
2. 以 `approval_policy = "on-request"` 讓 Codex 對 `claude` 呼叫請求升權，由人核准。
3. 未驗證：Codex execpolicy（`.rules` 的 `prefix_rule`）能否讓 `claude -p` 在 sandbox 外執行。

### 3.4 可直接複製的 Codex custom agent：`.codex/agents/claude-implementer.toml`

這份 role 檔與 2.4 對稱：Codex 的子代理只做薄包裝，實際工作交給 `claude -p`。下面 `claude -p` 這組旗標的組合已在 2.1.296 實測過：

- prompt 從 stdin 檔案讀入，搭配 `--tools`、`--permission-mode dontAsk`、`--output-format json`、`--json-schema`，回傳 `structured_output`（符合 schema）、`is_error: false`、`subtype: success`、`total_cost_usd`、`permission_denials: []`，`modelUsage` 的 key 是實際執行的模型（`claude-haiku-5-5`）。
- 加上 `--max-turns 1` 會讓執行回傳 `is_error: true`、`subtype: error_max_turns`，exit 1。

Codex 這一側（role 載入、繼承 sandbox）只依原始碼，**未實際執行**。

```toml
# .codex/agents/claude-implementer.toml   (project must be trusted; see 1.3.1)
name = "claude_implementer"
description = """Cross-vendor implementation lane that runs Anthropic Claude Code headless (`claude -p`). \
Use when you want a Claude model to implement a well-specified change. The caller must pass a complete spec \
(objective, files, interfaces, constraints, verification command). This agent never writes code itself: it drives \
claude, re-runs the verification, and returns a CLAUDE REPORT. Returns STATUS unavailable if the claude CLI is \
missing or not logged in."""
model = "gpt-6-luna"              # cheap wrapper model; pick one your account can use
model_reasoning_effort = "medium"
nickname_candidates = ["Claude Lane"]
developer_instructions = '''
You are a dispatcher and verifier. Anthropic Claude Code writes the code, not you.
Do not edit files yourself, do not finish claude's work, and never substitute your own
implementation when claude fails. Never spawn other agents.

1. PREFLIGHT (always first):
   command -v claude && claude --version && claude auth status --text
   `claude auth status` exits 0 when logged in and 1 when not. On any failure, stop and
   return the report from step 6 with STATUS: unavailable and the exact stderr.

2. PREPARE (fresh directory per run):
   RUN=$(mktemp -d "${TMPDIR:-/tmp}/claude-lane.XXXXXX")
   git status --porcelain > "$RUN/pre-status.txt" 2>/dev/null
   Write the caller's spec verbatim to "$RUN/spec.md" with a quoted heredoc (<<'SPEC_EOF').
   End it with: "Run the verification command and report its real output."
   Write this JSON Schema to "$RUN/schema.json":
   {"type":"object","additionalProperties":false,
    "required":["status","changes","verification","notes"],
    "properties":{
      "status":{"enum":["complete","partial","blocked"]},
      "changes":{"type":"array","items":{"type":"object","additionalProperties":false,
        "required":["file","summary"],"properties":{"file":{"type":"string"},"summary":{"type":"string"}}}},
      "verification":{"type":"object","additionalProperties":false,"required":["command","passed","output_tail"],
        "properties":{"command":{"type":"string"},"passed":{"type":"boolean"},"output_tail":{"type":"string"}}},
      "notes":{"type":"string"}}}

3. INVOKE CLAUDE (one shell call; allow it at least 660 s):
   TO=$(command -v timeout || command -v gtimeout)
   ${TO:+$TO --kill-after=15s 600s} claude -p \
     --model "${CLAUDE_MODEL:-opus}" \
     --effort "${CLAUDE_EFFORT:-high}" \
     --tools "Read,Edit,Write,Glob,Grep,Bash" \
     --permission-mode dontAsk \
     --allowedTools "Read,Edit,Write,Glob,Grep,Bash(<verification command> *),Bash(git diff *),Bash(git status *)" \
     --max-turns 40 \
     --max-budget-usd 5 \
     --no-session-persistence \
     --output-format json \
     --json-schema "$(cat "$RUN/schema.json")" \
     < "$RUN/spec.md" > "$RUN/result.json" 2> "$RUN/stderr.log"
   echo "exit=$?"
   Flag rationale:
   - The prompt comes from stdin via a file redirect.
   - --tools limits which tools exist. --allowedTools only pre-approves them.
   - dontAsk denies anything not pre-approved, because nobody can answer a prompt.
   - Never pass --dangerously-skip-permissions.
   - Replace <verification command> with the spec's command prefix, e.g. Bash(npm test *).
   - Use the model and effort the spec names; aliases are sonnet, opus, haiku, fable,
     or pass a full model id.

4. INTERPRET (read "$RUN/result.json"):
   - exit 0 and is_error false: success. Use .structured_output.
   - is_error true: STATUS invocation_error, unless subtype is error_max_turns
     (then STATUS partial).
   - exit 124 or 137 with timeout present: STATUS timeout.
   - Model actually used: the keys of .modelUsage. If they differ from the requested
     model, record a stand-in.
   - Cost: .total_cost_usd. Denied tools: .permission_denials.
   - If stderr shows a network or sandbox error, the parent sandbox blocked the
     Anthropic API: STATUS blocked_by_sandbox (see 3.3). Do not retry with weaker
     safety flags.

5. VERIFY independently:
   - Compare git status --porcelain and git diff --stat with "$RUN/pre-status.txt".
   - Re-run the verification command yourself and keep its real output.
   - Claude's own "passed" claim is not evidence.

6. OUTPUT (return exactly this, nothing else):
   CLAUDE REPORT
   STATUS: complete | partial | timeout | invocation_error | blocked_by_sandbox | unavailable
   MODEL_REQUESTED: <alias>  MODEL_USED: <modelUsage keys>  EFFORT: <effort>
   EXIT: <code>  RUN_DIR: <$RUN>  COST_USD: <total_cost_usd>
   OBJECTIVE: <one line>
   CHANGES:
   - <file> — <one-line summary from the actual diff>
   VERIFIED: <command you re-ran> -> <pass|fail>
   <last <=15 lines of its real output>
   CLAUDE SAID: <structured_output.status + notes, one line; note disagreement with the diff>
   DENIED_TOOLS: <permission_denials tool names or "none">
   GAPS: <open questions, missing deadline, or "none">
   REASON: <only for non-complete statuses: exact stderr tail or result text>
'''

[features]
memory_tool = false     # roles can only switch features OFF; shell_tool must stay on to run claude
```

**唯讀審查版（`claude-reviewer.toml`）的差異**：

- 第 3 步改成 `--tools "Read,Grep,Glob" --allowedTools "Read,Grep,Glob" --permission-mode dontAsk --max-turns 20`。
- schema 換成 5.4 的 `findings.schema.json`。
- 拿掉第 5 步。
- 第 6 步回傳 `CLAUDE REVIEW` 標頭與 `structured_output` 原文，不做任何編輯或排序。

**必須知道的 Codex 限制**：

1. 這份 role 檔若寫 `sandbox_mode`、`[sandbox_workspace_write]`、`[mcp_servers]`，在 f82e365 上都**不會**套用（1.3.3）。`claude -p` 能不能連上 Anthropic API，取決於**父 session** 的 sandbox 與網路設定（3.3）。
2. Role 無法像 Claude 的 `tools:` 那樣用白名單限制工具，只能關掉 feature。所以「包裝者不自己改檔」只能靠 instructions 約束；若父 session 是 read-only，claude 也改不了檔。實作 lane 需要父 session 是 `workspace-write`（且開網路）。
3. `--max-budget-usd` 用的是用戶端的成本估計，實際花費可能超過上限（`cli-reference`）。

**Codex plugin 內**：manifest 沒有 `agents`（1.4），plugin **無法**直接發佈這份 `.toml`。做法有兩種：

- 把它放在 plugin 中當範本（例如 `skills/<skill>/references/codex-roles/claude-implementer.toml`），在 README 或 skill 中指示複製到 `.codex/agents/` 或 `~/.codex/agents/`。
- 讓 skill 本身承載同一份步驟：SKILL.md 寫「spawn a `worker` agent with this message: …（第 1–6 步）」，或由主執行緒直接執行。Codex 會遵從 skill 中的委派指示（`subagents` 文件）。

SKILL.md 中的相對路徑會相對於 SKILL.md 所在目錄解析（1.4），所以第 3 步可以改成呼叫 skill 內附的腳本。

### 3.5 現有參考實作：`dispatch-claude-advisor.js`

它現在的呼叫是 `claude -p <brief> --system-prompt <agents/claude-advisor.md body> --model <primary> [--fallback-model …] --allowedTools Read,Grep,Glob --output-format json --no-session-persistence`（`scripts/dispatch-claude-advisor.js:108-110`），並回報 `modelUsed`、`degraded`、`degradeReason`（`references/dispatch-and-flags.md`）。

可直接沿用的有：persona 從 agent `.md` 讀取（讓 cc 與 Codex 兩條路徑用同一份 persona）、以 `modelUsage` 判斷實際執行的模型、對 credit 用盡（429）做 fallback。

建議修正：把 `--allowedTools Read,Grep,Glob` 改成（或加上）`--tools Read,Grep,Glob --permission-mode dontAsk`，因為 `--allowedTools` 不限制工具，而 `-p` 預設可能是 auto mode（3.2）。另外要考慮 `--max-turns`、`--max-budget-usd`；在不受信任的 repo 還要考慮 `--bare`。

---

## 4. 參考：cursor `pstack/interrogate` 如何分派給不同模型

Frontmatter 原文（`pstack/skills/interrogate/SKILL.md` @ `1dcc2ba`）：

```yaml
---
name: interrogate
description: "Use for \"interrogate\", \"adversarial review\", \"multi-model review\", \"challenge this\", \"stress test this code\", \"find blind spots\", or \"tear this apart\". Multiple LLM reviewers challenge changes from independent angles."
disable-model-invocation: true
---
```

流程：

1. **Scope**：使用者指定的檔案或 diff，或 `git diff main...HEAD`。
2. **Intent**：先寫一段意圖說明，不確定就問使用者。
3. **Spawn**：在**同一則訊息**中用 Task 工具平行啟動 reviewer，每個 reviewer 對應 `~/.cursor/rules/pstack-models.mdc` 中 `interrogate reviewers` 那一行的一個項目。預設兩個：`claude-opus-5-5-xhigh`、`grok-4.7-xhigh-fast`（`setup-pstack/SKILL.md` 第 65 行也一樣）。每個 reviewer 都是 `subagent_type: generalPurpose`、`readonly: true`，`model` 設為該項目；`auto`/`inherit-parent` 則省略 `model`。
   - 若 slug 被拒，就退回同家族（以 `claude-*`/`grok-*` 前綴判斷）的預設值，**並說明**。不讓 slug 問題擋住審查。
4. **Prompt**：所有 reviewer 用同一份模板（`references/reviewer-prompt.md`：intent、diff、rubric、code-quality lens；severity 為 `critical|warning|nit`；「no findings」也是合法結果）。
5. **Synthesize**：合併重複項，記錄是哪些模型提出的。兩個以上模型各自獨立提出的發現訊號最強。
6. **Lead Judgment**：主審把每個發現分到 Act on / Consider / Noted / Dismissed 四桶（`references/lead-judgment.md`：nitpick gravity、hypothetical vs actual 等過濾原則），最後輸出 Agreement Map。不自動修改。

Manifest：`pstack/plugin.json`（Agent Plugins `$schema`，v0.15.21）與 `.cursor-plugin/plugin.json`（`"skills": "./skills/"`、`"agents": "./agents/"`）。

**關鍵差異**：interrogate 的「多廠商」**完全依賴 Cursor 的 Task 工具能直接以 `model` 參數挑選不同廠商的模型**，所以它沒有任何 CLI 包裝層。Claude Code 的 Agent 工具與 Codex 的 `spawn_agent` 都只能選**自家**模型（cc：`sonnet/opus/haiku/fable`；Codex：`model` slug），要跨廠商就必須走第 2、3 節的 CLI lane。

可借鏡的有：reviewer 名單放在可設定的單一來源、slug 失敗時退回同家族並說明、所有 reviewer 用同一份 prompt 模板、主審不只做彙整而要判斷。review-forge 已經有 cross-vote 與加權 confidence（比 interrogate 的「兩個以上模型同意」更量化），兩者可以互補：interrogate 的四桶可以作為 `report` 之後的人類判斷輔助，但**不取代** checkbox 核准邊界。

---

## 5. 目標三：review-forge 多廠商化設計

### 5.1 現況

`plugins/code-review/skills/review-forge/SKILL.md` 定義了 `review → synthesize → vote → report → fix → verify`，每一個 `review` 或 `vote` 都是「一個模型寫一個檔」（`<model>.md`、`<model>-vote.md`），`sources` 用來做 abstain，`model_weights` 用來加權。但它**沒有寫要由誰、怎麼啟動其他模型**，實際上只能由使用者在不同 host 手動各跑一次，或由 host 用自家模型扮演多個名字。`evals/evals.json` 目前只測 `vote`（abstain）與 `report`（加權分數）。

### 5.2 Lane 模型

在 `review` / `vote` 之上加一個 orchestration 層（新命令 `fanout`，或寫成 `review`/`vote` 的 `lanes:` 輸入）。每條 lane = (host 機制, 模型 slug, 檔名用的 model 名稱)：

| Host | 同廠商 lane | 跨廠商 lane |
|---|---|---|
| Claude Code | Agent 工具派 `code-review:forge-reviewer`，用 per-invocation `model` 參數分別帶 `opus`、`sonnet`（或 `fable`） | `code-review:codex-reviewer`（2.4 的審查版：inline `codex exec -s read-only --output-schema`，或改走 dispatcher） |
| Codex | `spawn_agent`，`agent_type` 指向 `forge_reviewer_sol`、`forge_reviewer_luna` 這類 role（role 鎖定 `model` 與 effort） | 主執行緒或 `worker` 執行 `scripts/dispatch-claude.js`（`claude -p --tools Read,Grep,Glob --permission-mode dontAsk --output-format json --json-schema …`） |

規則：

- **檔名用實際執行的模型**：cc 取 `/tasks` 或 lane 回報的模型；Claude CLI 取 `modelUsage`；Codex 取請求的 slug。lane 被替身取代時，檔名用替身模型，並在報告標註 stand-in（沿用 advisor「Name the stand-in」原則）。不能讓 `sources` 與 abstain 認錯人。
- **一條 lane 一個檔**，保持 review-forge 原本的輸出邊界。包裝 agent 負責寫檔；CLI 在 read-only sandbox 只回傳 JSON。
- **vote 也走同一組 lane**。每條 lane 的 brief = `summary.md` + diff 指標 + 「abstain on findings whose `sources` include `<model>`」，並且不提供其他 `*-vote.md`，以保持獨立。
- `synthesize` 與 `report` 由 host 主執行緒做。這兩步是確定性的彙整，`report` 的分數公式不變。

### 5.3 檔案佈局（建議）

```text
plugins/code-review/
  .claude-plugin/plugin.json
  .codex-plugin/plugin.json
  agents/                              # 只有 Claude Code 讀（Codex manifest 無 agents）
    forge-reviewer.md                  # 同廠商 reviewer/voter：tools Read,Grep,Glob,Bash(唯讀 git)
    codex-reviewer.md                  # 跨廠商（cc → Codex）
  skills/review-forge/
    SKILL.md                           # 新增「Lanes」一節：preflight、fan-out、失敗處理
    agents/openai.yaml                 # 既有 Codex skill metadata
    references/lanes.md                # 兩個 host 各自的 lane 表、預設名單、成本上限
    references/codex-roles/            # 給使用者複製到 .codex/agents/ 的 role 範本
      forge-reviewer-sol.toml
      forge-reviewer-luna.toml
      claude-reviewer.toml
    scripts/dispatch-codex.js          # 由 advisor 移入或共用（見 §7）
    scripts/dispatch-claude.js         # 由 dispatch-claude-advisor.js 一般化
    assets/schemas/findings.schema.json
    assets/schemas/votes.schema.json
    assets/templates/...               # 既有
    evals/evals.json                   # 新增 lane 失敗與 stand-in 的案例
```

Project 層級的覆寫（雲端 session 或想固定名單時）：`.claude/agents/codex-reviewer.md`、`.codex/agents/*.toml`，以及 `.review/lanes.yml`（可選，對應 interrogate 的 `pstack-models.mdc`）。

### 5.4 定義範例

`agents/forge-reviewer.md`（cc 同廠商；以 per-invocation `model` 參數切換 opus/sonnet）：

```markdown
---
name: forge-reviewer
description: Read-only review-forge reviewer/voter. Given a review or vote brief, inspects the diff and code and returns findings or votes as JSON matching the review-forge schema. Never edits files, never spawns agents.
tools: Read, Grep, Glob, Bash
disallowedTools: Edit, Write
skills:
  - code-review:review-forge
maxTurns: 30
---
Follow the brief exactly. Only run read-only git commands (git diff, git show, git log).
Return only JSON matching the schema named in the brief.
```

`references/codex-roles/forge-reviewer-sol.toml`（Codex 同廠商）：

```toml
name = "forge_reviewer_sol"
description = "Read-only review-forge reviewer/voter on the Sol tier. Returns findings or votes as JSON per the review-forge schema."
model = "gpt-6.1-sol"
model_reasoning_effort = "high"
developer_instructions = """
Follow the review-forge brief. Do not edit files. Do not spawn agents.
Return only JSON matching the schema named in the brief.
"""
```

`assets/schemas/findings.schema.json`（兩端共用，對應 `review_report.md` 欄位）：

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": ["model", "findings"],
  "properties": {
    "model": { "type": "string" },
    "findings": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["severity", "affected_files", "evidence", "risk", "suggested_fix", "suggested_tests"],
        "properties": {
          "severity": { "enum": ["critical", "high", "medium", "low", "note"] },
          "affected_files": { "type": "array", "items": { "type": "string" } },
          "evidence": { "type": "string" },
          "risk": { "type": "string" },
          "suggested_fix": { "type": "string" },
          "suggested_tests": { "type": "string" }
        }
      }
    }
  }
}
```

### 5.5 失敗處理

1. **Preflight 全部 lane 再分派**：`command -v codex && codex login status`；`command -v claude && claude auth status`（兩者都是 exit 0 / 1）。不通過的 lane 狀態記為 `unavailable`，不啟動。
2. **不靜默替代**：跨廠商 lane 失敗時，**不能**由 host 模型冒名寫 `gpt-*.md` 或 `opus-*.md`。可以用另一條 lane 補位，但要在 `final-report.md` 標成 stand-in。
3. **Quorum**：`report` 新增 `vendor_families` 欄位。少於兩個廠商家族時，報告標成 `single_vendor`，並在 Reviewer Notes 說明缺少哪條 lane；分數照算。review-forge 已有「missing voters」機制可以直接沿用。
4. **Timeout / invocation_error**：沿用 dispatcher 的四種狀態。`timeout` 時，部分輸出不寫進 `.review/`；重派前先確認 `--pidfile` 中的 PID 已經結束（advisor 的「Cancel is not dead」）。
5. **Schema 驗證失敗**：lane 回傳非 JSON 或不符合 schema 時，記為 `invocation_error`，原文存到 `.review/<feature>/.raw/<model>.txt` 供人檢查。不自行修補內容。

### 5.6 成本、逾時與併發

- **CLI deadline**：dispatcher 預設 600s，必須小於 Claude Bash 上限 10 分鐘。超過時要在 Bash 呼叫上設 `timeout`，或改背景執行。
- **Claude lane**：加 `--max-turns`、`--max-budget-usd`，並從 `--output-format json` 讀 `total_cost_usd` 記錄到 `status.md`。
- **Codex lane**：用 `--json` 讀 `turn.completed.usage`，並以 `[agents] max_concurrent_threads_per_session` 限制 Codex host 的併發。
- **cc host 的併發上限**：見 `sub-agents` 的「Concurrent subagent limit」（細節沒有在本文展開）。
- **預設名單建議**：每個 host「1 條同廠商強模型 + 1 條同廠商快模型 + 1 條跨廠商」，共 3 個 reviewer。vote 階段用同樣 3 條 lane。
- **注意**：`CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` 會讓 cc 同廠商的所有 lane 都跑同一個模型，等於失去同廠商多樣性。preflight 要檢查並警告。

### 5.7 對 SKILL.md 與 evals 的具體改動

- 新增 `lanes` 輸入（`host-native:<model>`、`codex:<slug>`、`claude:<alias>`），並新增「Lanes」一節：preflight → 平行分派（cc 在同一則訊息發出多個 Agent 呼叫，Codex 一次 spawn 多個）→ 寫檔 → 回報 lane 狀態表。
- `report` 新增 `vendor_families` 與 `stand_ins` 兩個欄位；`final_report.md` 模板同步更新。
- evals 新增三個案例：
  1. codex 不在 PATH：只產出同廠商檔案，報告標 `single_vendor`，且沒有冒名的 `gpt-*.md`。
  2. lane timeout：不寫 partial 檔。
  3. stand-in：檔名用替身模型，並標註 stand-in。

---

## 6. Claude Code 與 Codex 對照表

| 面向 | Claude Code（2.1.296 + docs） | Codex（`f82e365` + docs） |
|---|---|---|
| 專案 subagent 位置 | `.claude/agents/*.md`（YAML frontmatter + 內文 prompt） | `.codex/agents/**/*.toml`，或 `.codex/config.toml` 的 `[agents.<name>] config_file=` |
| 必填欄位 | `name`、`description` | `name`、`description`、`developer_instructions` |
| 指定模型 | `model`（alias/ID/inherit）、`effort` | `model`、`model_reasoning_effort`（鎖定，spawn 時不能改） |
| 工具限制 | `tools`、`disallowedTools`（白名單） | 只能以 `[features]` 關閉 `shell_tool/apps/plugins/memory_tool/request_permissions_tool` |
| Sandbox / 權限 | `permissionMode`（plugin agent 會忽略；父為 auto/bypass/acceptEdits 時也會忽略） | 一律繼承父 session（role 的 `sandbox_mode` 會被丟掉；文件說法不同） |
| 子代理專屬 MCP | `mcpServers`（plugin agent 會忽略） | 不支援（role 的 `mcp_servers` 會被丟掉；文件說法不同） |
| 預載 skill | `skills:`（完整內容，可用 `plugin:skill`，已實測） | 沒有；只能停用 skill |
| plugin skill/MCP 在子代理中可用 | 可用（依 `tools` 白名單） | 繼承父 session，預設可用 |
| plugin 能否發佈 agent | 可以（`agents/`，名稱為 `plugin:name`） | **不能**（manifest 沒有 `agents`），只能由 skill 承載腳本與指示 |
| 專案啟用 plugin | `.claude/settings.json` 的 `enabledPlugins` + `extraKnownMarketplaces`（要 trust） | `.agents/plugins/marketplace.json` + `.codex/config.toml` 的 `[plugins."x@m"] enabled=true`（要 trust） |
| 雲端 | repo 宣告的 plugin 不安裝；`.claude/agents/` 會帶過去 | 未研究（ChatGPT Work 由託管環境處理） |
| 非互動 CLI | `claude -p --output-format json [--json-schema] --model --permission-mode --tools --max-turns --max-budget-usd` | `codex exec - -m <slug> -c model_reasoning_effort=… -s read-only -C <dir> -o <file> [--output-schema] [--json] [--ephemeral]` |
| 認證檢查 | `claude auth status`（0/1） | `codex login status`（0/1） |
| 當作 MCP server | `claude mcp serve` 只開放工具，不是代理 | `codex mcp-server` **已移除** |

---

## 7. 建議（本 repo）

1. **把 dispatcher 共用化**：`dispatch-codex.js` 目前放在 `plugins/advisor/skills/orchestration/scripts/`，code-review 用不到（plugin 之間不共用檔案）。可以複製到 `plugins/code-review/skills/review-forge/scripts/`，並加上同步檢查（例如 CI 用 `diff` 比對兩份），或抽到 repo 根目錄的 `tools/review-lanes/` 由兩個 plugin 打包。Claude 的 plugin dependencies 只對 Claude 有效，Codex 沒有對應機制，所以不採用。
2. **新增審查專用的 lane**：`code-review` plugin 新增 `agents/codex-reviewer.md`（cc → Codex）與 `scripts/dispatch-claude.js`（Codex → Claude，由 `dispatch-claude-advisor.js` 一般化：persona 檔參數化、加上 `--tools`、`--permission-mode dontAsk`、`--json-schema`、`--max-turns`）。
3. **review-forge SKILL.md 加上 Lanes 一節**（5.2、5.5、5.7），並以 evals 鎖住「不冒名」「單一廠商標記」兩條行為。
4. **Codex 端以 skill 為主**，role 範本只當作「建議複製」的參考。不要在 role 檔寫 `sandbox_mode`、`mcp_servers`，因為 f82e365 不會套用；README 要寫明子代理繼承父 sandbox，跨廠商 lane 需要網路。
5. **修 advisor 的 Claude 呼叫**：`--allowedTools Read,Grep,Glob` 改成 `--tools Read,Grep,Glob --permission-mode dontAsk`（3.2、3.5）。
6. **模型 slug 不要寫死在多處**：advisor 寫的是 `gpt-5.6-sol`，而 Codex 文件目前推薦 `gpt-6.1-sol`、`gpt-6-luna`。lane 名單集中到 `references/lanes.md`（或 `.review/lanes.yml`），仿照 interrogate 的單一設定來源與同家族退回機制。
7. **雲端與自動載入**：要讓團隊預設可用，就在使用端 repo 的 `.claude/settings.json` 宣告 marketplace 與 plugin。要讓雲端 session 也可用，就把 `codex-reviewer.md` 放進 `.claude/agents/`，因為雲端不裝 repo 宣告的 plugin；同時也要接受雲端通常沒有 `codex` CLI，lane 會回報 `unavailable`。

---

## 8. 未驗證事項清單

- Codex 的所有執行期行為：本環境沒有 `codex`，只讀了原始碼與文件。包括 `--output-schema` 的 strict 要求、`codex exec` 沒有內建逾時、在 Codex sandbox 中執行 `claude -p` 的網路與寫入限制，以及 execpolicy 是否能讓它在 sandbox 外執行。
- Codex「role 會丟掉 `sandbox_mode`/`mcp_servers`」只綁定在 main `f82e365`。release 版本是否相同無法查證（`gh api` 回 403）；文件說法相反。
- 2.4 與 3.4 的 agent 檔：`claude plugin validate` 驗過 2.4 的 frontmatter；`tomllib` 驗過 3.4 的 TOML 語法；2.4 第 3 步在沒有 codex 時回 exit 127（已測）；3.4 第 3 步的 `claude -p` 旗標組合已實測（見 3.4 開頭）。**沒有**端到端跑過 Codex 實際寫碼或 Codex 載入該 role。
- Claude Code：在 `mcpServers:` 中以 `"plugin:<p>:<s>"` 引用 plugin server、`.claude/agents/` 內文的 `${CLAUDE_PROJECT_DIR}` 替換與 Bash 環境變數、`Bash(node *dispatch-codex.js*)` 權限規則寫法。
- Codex 雲端（ChatGPT Work）環境中的 plugin 與 custom agent 行為：沒有研究。

# skills

coding-agent-toolkit 自行維護的 skill 集合，一個插件同時支援 Claude Code、Codex 與 Pi。

```text
/plugin install skills --marketplace gn00678465/coding-agent-toolkit
```

Codex 與 Pi 的安裝方式見根目錄 [README](../../README.md)。

| Skill | 說明 |
|-------|------|
| `pull-request` | 建立與修改 GitHub PR，也負責建立 PR 模板 |
| `issue-template` | 建立、重構與驗證 GitHub Issue Forms 模板 |
| `review-forge` | 多模型程式碼審查：獨立審查 → 交叉投票 → 信心排序 → 核准修復 |
| `slim-agents-md` | 精簡與重構 AGENTS.md / CLAUDE.md |
| `ui-design` | 把 UI 需求委派給 `impeccable-ui-designer` agent |

## impeccable-ui-designer

`ui-design` skill 本身不做設計，而是交給 `agents/impeccable-ui-designer.md`：

- **Claude Code**：plugin 會自動載入 `agents/`，agent 名稱為 `skills:impeccable-ui-designer`。
- **Codex**：plugin 不會載入 subagent，請把 `.codex/agents/impeccable-ui-designer.toml` 複製到專案的 `.codex/agents/`。
- **Pi**：裝了 `@tintinweb/pi-subagents` 時透過 `pi.subagents` 註冊；否則 `ui-design` 走 inline 模式，直接讀取 `agents/impeccable-ui-designer.md` 執行。

agent 需要 impeccable skill：`npx impeccable install --providers=claude,codex`，或 `/plugin install impeccable@coding-agent-toolkit`。

`.codex/agents/impeccable-ui-designer.toml` 是 `agents/impeccable-ui-designer.md` 的 Codex 版，修改 agent 時兩份要一起更新。

## 授權

MIT。`impeccable-ui-designer` 的角色內容改寫自 [agency-agents 的 design-ui-designer](https://github.com/msitarzewski/agency-agents/blob/main/design/design-ui-designer.md)（MIT，Copyright (c) 2025 AgentLand Contributors），授權全文見 [upstream LICENSE](https://github.com/msitarzewski/agency-agents/blob/4e3ac3ca6604c75113f52c695dbddcc7af928b46/LICENSE)。impeccable（Apache-2.0）不隨本插件散布。

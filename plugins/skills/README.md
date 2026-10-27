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
| `subtractive-engineering` | 減法工程：以奧坎剃刀原則擋下多餘的元件、抽象與 prompt 規則，先刪除再新增。設定了 `disable-model-invocation`，只能手動叫用（`/skills:subtractive-engineering <需求>`） |
| `ui-design` | 把 UI 需求委派給 `impeccable-ui-designer` agent |

## Agents

| Agent | 說明 |
|-------|------|
| `impeccable-ui-designer` | `ui-design` skill 的設計執行者，所有設計決策交給 impeccable skill |
| `subtractive-brake` | 奧坎剃刀審查員：在新增元件、middleware、lock、cron、設定或 prompt 規則前審查，輸出 Razor Verdict |

- **Claude Code**：plugin 會自動載入 `agents/`，agent 名稱為 `skills:impeccable-ui-designer`、`skills:subtractive-brake`。
- **Codex**：plugin 不會載入 subagent，請把 `.codex/agents/` 底下需要的 `.toml` 複製到專案的 `.codex/agents/`。
- **Pi**：裝了 `@tintinweb/pi-subagents` 時，兩個 agent 都透過 `pi.subagents` 註冊。沒裝時 `ui-design` 走 inline 模式，直接讀取 agent 定義執行。`subtractive-brake` agent 的 `tools` 寫的是 Claude Code 的工具名稱（`Read`、`Grep`、`Glob`、`Bash`），在 Pi 上的行為尚未驗證。

`impeccable-ui-designer` 需要 impeccable skill：`npx impeccable install --providers=claude,codex`，或 `/plugin install impeccable@coding-agent-toolkit`。

`subtractive-brake` 的 frontmatter 有 `readonly: true`，但 Claude Code 與 Codex 都不會依這個欄位限制寫入（agent 仍有 `Bash`），read-only 只靠 agent 指示本身。

`.codex/agents/*.toml` 是 `agents/*.md` 的 Codex 版（只保留 `name`、`description` 與 `developer_instructions`）。修改 agent 後，用 [apm-go](https://github.com/gn00678465/apm-go) 重新產生：

```bash
# 安裝 apm-go
curl -fsSL https://raw.githubusercontent.com/gn00678465/apm-go/main/install.sh | sh

# 在暫存目錄把 agent 轉成 Codex TOML，再複製回來
tmp=$(mktemp -d)
mkdir -p "$tmp/.apm/agents"
for f in plugins/skills/agents/*.md; do
  cp "$f" "$tmp/.apm/agents/$(basename "$f" .md).agent.md"
done
printf 'name: tmp\nversion: 0.0.1\ntargets:\n- codex\n' > "$tmp/apm.yml"
(cd "$tmp" && apm-go install)
cp "$tmp"/.codex/agents/*.toml plugins/skills/.codex/agents/
```

## 授權

MIT。`impeccable-ui-designer` 的角色內容改寫自 [agency-agents 的 design-ui-designer](https://github.com/msitarzewski/agency-agents/blob/main/design/design-ui-designer.md)（MIT，Copyright (c) 2025 AgentLand Contributors），授權全文見 [upstream LICENSE](https://github.com/msitarzewski/agency-agents/blob/4e3ac3ca6604c75113f52c695dbddcc7af928b46/LICENSE)。impeccable（Apache-2.0）不隨本插件散布。

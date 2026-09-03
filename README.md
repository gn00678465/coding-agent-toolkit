# coding-agent-toolkit

本專案收錄多個可重用的 AI 編碼代理插件，支援 Claude Code、Codex 及 OpenCode 等平台。

## 插件清單

| 插件 | 版本 | 適用平台 | 說明 |
|------|------|----------|------|
| `git-assistant` | 0.1.4 | Claude Code / Codex | Commit / PR 工作流插件，包含 `commit-message`、`pull-request` 等技能 |
| `advisor` | 0.1.4 | Claude Code / Codex | 架構師模式 model-routing：session 跑在 Claude 最強模型上負責規格與驗證，實作路由給 Grok 4.5（Grok CLI）與 GPT-5.6 Sol（Codex），並提供承諾邊界 advisor |
| `code-review` | 0.2.0 | Claude Code / Codex / OpenCode | 程式碼審查與驗證：`review-forge` 多模型審查工作流（獨立審查 → 交叉投票 → 信心排序 → 核准修復），`verification-gate` 完工後的驗證關卡與 evidence 報告 |
| `slim-agents-md` | 0.1.0 | Claude Code / Codex | 以 progressive disclosure 原則精簡肥大的 AGENTS.md / CLAUDE.md：矛盾裁決 → root 本質萃取 → 分類拆檔 → 標記刪除 → 確認後落地 |

## 外部套件

以下為透過 marketplace 轉發的第三方 skill 套件，皆以 commit sha 鎖定版本：

| 套件 | GitHub | 分類 | 授權 |
|------|--------|------|------|
| `web-quality-skills` | https://github.com/addyosmani/web-quality-skills | Productivity | MIT |
| `impeccable` | https://github.com/pbakaus/impeccable | design | Apache-2.0 |
| `taste-skill` | https://github.com/Leonxlnx/taste-skill | design | MIT |
| `beautify-github-readme` | https://github.com/oil-oil/beautify-github-readme | design | MIT |
| `show-me` | https://github.com/humanlayer/skills/tree/main/plugins/show-me | Productivity | MIT |
| `reviewable-html-workbench` | https://github.com/u-ichi/reviewable-html-workbench | Productivity | MIT |
| `archify` | https://github.com/tt-a1i/archify | Productivity | MIT |

安裝方式與本專案插件相同，例如：`/plugin install impeccable@coding-agent-toolkit`。

### 授權說明

授權欄位為各套件在本專案鎖定的 commit sha 上實際查得的授權，皆與本專案的 MIT 相容。本專案不散布這些套件的程式碼，marketplace 僅保存 URL 與 commit sha 指標，安裝時由使用者端自 upstream 取得，因此授權義務適用於使用者本地的副本。

- `impeccable` 為 **Apache-2.0**，非 MIT。使用時須額外保留其 `NOTICE.md`，修改檔案時須標示變更；該套件內容不會因併入本 marketplace 而變更授權。
- `show-me` 的 MIT 授權檔位於 `humanlayer/skills` 的 repo 根目錄，未包含在 `plugins/show-me` 子目錄內，因此以子目錄方式安裝時不會帶入授權檔，請自行參照 upstream 的 [LICENSE](https://github.com/humanlayer/skills/blob/main/LICENSE)。
- `archify` 內建的品牌 logo 向量不受其 MIT 涵蓋，個別圖示另有授權與商標限制（例如 Vue.js 為 CC-BY-NC-SA-4.0），詳見 upstream 的 [THIRD_PARTY_NOTICES.md](https://github.com/tt-a1i/archify/blob/main/archify/THIRD_PARTY_NOTICES.md)。

## Claude Code 安裝方式

先加入 Marketplace 來源：

```text
/plugin marketplace add gn00678465/coding-agent-toolkit
```

再依需求安裝插件：

**option1**
```text
/plugin install git-assistant@coding-agent-toolkit
/plugin install advisor@coding-agent-toolkit
/plugin install code-review@coding-agent-toolkit
/plugin install slim-agents-md@coding-agent-toolkit
/reload-plugins
```

**option2**
.claude/settings.json
```
{
  "enabledPlugins": {
    "git-assistant@coding-agent-toolkit": true,
    "advisor@coding-agent-toolkit": true,
    "code-review@coding-agent-toolkit": true,
    "slim-agents-md@coding-agent-toolkit": true
  }
}
```

安裝完成後可使用：

- `git-assistant`: `commit-message`、`pull-request`
- `advisor`: `orchestration` skill 與 `claude-advisor`、`grok-implementer`、`codex-implementer` agents
- `code-review`: `review-forge` skill（`review` / `synthesize` / `vote` / `report` / `fix` / `verify` 六階段命令）與 `verification-gate` skill（`gate` / `evidence` 兩階段命令）
- `slim-agents-md`: `slim-agents-md` skill（AGENTS.md / CLAUDE.md 等 agent 指令文件的精簡與重構）

> `advisor` 另需先安裝 [Grok CLI](https://x.ai/cli) 與 Codex CLI，並確認 `grok`、`codex` 可於 `PATH` 中執行。

## Codex 安裝方式

先加入 Marketplace 來源：

```text
codex plugin marketplace add gn00678465/coding-agent-toolkit
```

再依需求安裝插件：

```text
codex plugin add git-assistant@coding-agent-toolkit
codex plugin add advisor@coding-agent-toolkit
codex plugin add code-review@coding-agent-toolkit
codex plugin add slim-agents-md@coding-agent-toolkit
```

每個 skill 目錄內含 `agents/openai.yaml` 提供 Codex UI 顯示名稱與預設 prompt。

## OpenCode 安裝方式

**方式一：透過 opencode-market（推薦）**

```bash
# 註冊 marketplace
npx opencode-market add gn00678465/coding-agent-toolkit

# 安裝到 .opencode/（OpenCode 專用）
npx opencode-market install code-review@coding-agent-toolkit --opencode

# 或安裝到 .agents/（跨平台共用）
npx opencode-market install code-review@coding-agent-toolkit --local
```

**方式二：手動複製 skill 目錄**

將 skill 複製到專案的 `.opencode/skills/`，OpenCode 會自動發現：

```bash
cp -r plugins/code-review/skills/review-forge .opencode/skills/
cp -r plugins/code-review/skills/verification-gate .opencode/skills/
```

## 目錄

- [`plugins/advisor`](./plugins/advisor)
- [`plugins/git-assistant`](./plugins/git-assistant)
- [`plugins/code-review`](./plugins/code-review)
- [`plugins/slim-agents-md`](./plugins/slim-agents-md)

## 參考

- [Claude Code Plugins](https://docs.anthropic.com/en/docs/claude-code/plugins)
- [Codex Agent Skills](https://github.com/openai/skills)
- [OpenCode Plugins](https://opencode.ai/docs/plugins/)
- [OpenCode Skills](https://opencode.ai/docs/skills/)

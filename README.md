# coding-agent-toolkit

本專案收錄多個可重用的 AI 編碼代理插件，支援 Claude Code、Codex 及 Pi 等平台。

## 插件清單

| 插件 | 版本 | 適用平台 | 說明 |
|------|------|----------|------|
| `git-assistant` | 0.1.7 | Claude Code / Codex / Pi | PR / Issue 模板工作流插件，包含 `pull-request`、`issue-template` 等技能 |
| `advisor` | 0.1.4 | Claude Code / Codex | 架構師模式 model-routing：session 跑在 Claude 最強模型上負責規格與驗證，實作路由給 Grok 4.5（Grok CLI）與 GPT-5.6 Sol（Codex），並提供承諾邊界 advisor |
| `code-review` | 0.3.0 | Claude Code / Codex / Pi | 程式碼審查與驗證：`review-forge` 多模型審查工作流（獨立審查 → 交叉投票 → 信心排序 → 核准修復），`verification-gate` 完工後的驗證關卡與 evidence 報告 |
| `slim-agents-md` | 0.1.0 | Claude Code / Codex / Pi | 以 progressive disclosure 原則精簡肥大的 AGENTS.md / CLAUDE.md：矛盾裁決 → root 本質萃取 → 分類拆檔 → 標記刪除 → 確認後落地 |
| `ui-design` | 0.1.0 | Claude Code / Codex / Pi | `ui-design` skill 自動把 UI 需求委派給 `impeccable-ui-designer` subagent；agent 以 design-ui-designer 角色為基礎，所有設計決策交由 impeccable skill（需另外安裝 `impeccable`） |

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
| `open-steps` | https://github.com/kharmanskyi/open-steps | Productivity | MIT |
| `pstack` | https://github.com/cursor/plugins/tree/main/pstack | Productivity | MIT |

安裝方式與本專案插件相同，例如：`/plugin install impeccable@coding-agent-toolkit`。

### 自動更新

[`.github/workflows/upstream-update.yml`](./.github/workflows/upstream-update.yml) 每天台灣時間 00:00 檢查外部套件的上游：

1. `apm-go marketplace outdated` 列出可更新的套件。
2. `apm-go marketplace package update` 把 `apm.yml` 的鎖定移到新 tag（有 `version` 的套件）或預設分支最新 commit（沒有 `version` 的套件；有 `subdir` 時只在子目錄內容有變動才移動）。
3. `apm-go pack --claude-source-style url` 重新產生兩份 `marketplace.json`，`apm-go marketplace check` 確認每個 ref 都存在。
4. 有變動時在 `bot/upstream-update` 分支開 PR 並直接 squash 合併。

需要先在 Settings → Actions → General 開啟「Allow GitHub Actions to create and approve pull requests」。也可以在 Actions 頁面手動執行，勾選 `dry_run` 只看差異、不建立 PR。授權欄位是依舊的鎖定 commit 查得的，套件更新後請留意上游是否變更授權。

`apm-go` 的版本固定在 workflow 的 `APM_GO_VERSION`，安裝腳本與 binary 都從同一個 tag 下載，上游發布新版不會影響排程。要升級時修改 `APM_GO_VERSION`，合併後手動以 `dry_run` 執行一次，確認 `marketplace.json` 的差異只有套件更新、沒有格式變動。

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
/plugin install ui-design@coding-agent-toolkit
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
    "slim-agents-md@coding-agent-toolkit": true,
    "ui-design@coding-agent-toolkit": true
  }
}
```

安裝完成後可使用：

- `git-assistant`: `pull-request`、`issue-template`
- `advisor`: `orchestration` skill 與 `claude-advisor`、`grok-implementer`、`codex-implementer` agents
- `code-review`: `review-forge` skill（`scope` / `review` / `synthesize` / `vote` / `report` / `fix` / `verify` 七階段命令，可透過 Codex / Claude Code CLI 跨廠商審查）與 `verification-gate` skill（`gate` / `evidence` 兩階段命令）
- `slim-agents-md`: `slim-agents-md` skill（AGENTS.md / CLAUDE.md 等 agent 指令文件的精簡與重構）
- `ui-design`: `ui-design` skill（自動觸發並轉介 UI 需求）與 `impeccable-ui-designer` agent（以 impeccable skill 進行 UI 設計、design system 建立與審查）

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

`ui-design` 的 subagent 無法透過 Codex plugin 載入，請在專案中以 `apm-go install gn00678465/coding-agent-toolkit/plugins/ui-design --target codex` 部署到 `.codex/agents/`，詳見 [`plugins/ui-design`](./plugins/ui-design)。

每個 skill 目錄內含 `agents/openai.yaml` 提供 Codex UI 顯示名稱與預設 prompt。

## Pi 安裝方式

Pi 沒有 marketplace，安裝單位是整個 repo。repo 根目錄的 `package.json` 用 `pi` 欄位列出可載入的資源。

```bash
# 使用者層級（專案層級加 -l，需先信任專案）
pi install git:github.com/gn00678465/coding-agent-toolkit
```

| 套件 | Pi 安裝方式 | 說明 |
|------|-------------|------|
| `git-assistant` | 隨上面的指令一起安裝 | `pull-request`、`issue-template` 兩個 skill，加上 `/gitignore-generator.prompt` 指令 |
| `code-review` | 隨上面的指令一起安裝 | 載入 `review-forge` 與 `verification-gate`。Pi 沒有 `host` lane，多模型 review 改用 `claude:` 與 `codex:` CLI lane，需要另外安裝並登入 `claude` 與 `codex` |
| `slim-agents-md` | 隨上面的指令一起安裝 | Pi 沒有 AskUserQuestion，矛盾裁決會改成在對話中直接詢問 |
| `ui-design` | 隨上面的指令一起安裝；要用 subagent 再裝 `pi install npm:@tintinweb/pi-subagents` | 有裝 [`@tintinweb/pi-subagents`](https://github.com/tintinweb/pi-subagents) 時，`package.json` 的 `pi.subagents` 會註冊 `impeccable-ui-designer`，`ui-design` 用 Agent tool 委派給它。沒裝時改用 inline 模式，在主 session 讀取 agent 定義並照著執行，遇到需要決定的地方直接問你。Pi 上模型不一定會自動載入 skill，建議用 `/skill:ui-design <需求>` 呼叫 |
| `impeccable` | 隨上面的指令一起安裝 | package 內的 extension（`pi/extensions/upstream-skills.ts`）在 Pi 啟動時，依 `.claude-plugin/marketplace.json` 鎖定的 commit，只下載上游的 `.pi/skills`（約 4 MB）到 `~/.pi/agent/cache/coding-agent-toolkit/`。第一次需要網路與 git。也可以改用官方安裝程式 `npx impeccable install --providers=pi` |
| `pstack` | 兩步驟，見下方 | 上游放在 `cursor/plugins` 的子目錄，Pi 的 git 來源不能指定子目錄 |

`pstack`：先安裝整個 `cursor/plugins` repo（不會載入任何資源），再在 `~/.pi/agent/settings.json` 指定 skill 路徑：

```bash
pi install git:github.com/cursor/plugins@9b93e81fb2921b9263d9463c15bafeabfe3903aa
```

```json
{
  "skills": ["git/github.com/cursor/plugins/pstack/skills"]
}
```

使用者層級 settings 的相對路徑以 `~/.pi/agent/` 為基準。pstack 大多數 skill 設了 `disable-model-invocation: true`，要用 `/skill:<name>` 手動呼叫。它的 `recall` skill 會和同名 skill 衝突，Pi 只保留先找到的那一個。

`impeccable-ui-designer` 只有在本 package 裝在使用者層級，或專案已儲存信任決定後，才會出現在 Agent tool 的可用清單。以 `-l` 裝在專案、且還沒儲存信任時，`pi-subagents` 第一個 session 不會把它告訴模型，`ui-design` 會改走 inline 模式。另一個同名套件 `pi-subagents`（nicobailon）也讀同一個 `pi.subagents` 欄位，但未經測試。

extension 是會執行的程式碼，Pi 會在信任 package 後才載入。要加入其他外部套件，在 `pi/upstreams.json` 加上套件名稱與 skill 目錄即可，版本跟著 `apm.yml` 的鎖定走。

裝完在 session 內執行 `/reload`。可以在 git 來源後加 `@<tag>` 鎖定版本。調查過程與限制見 [`docs/research/pi-package-install.md`](./docs/research/pi-package-install.md)。

## 目錄

- [`plugins/advisor`](./plugins/advisor)
- [`plugins/git-assistant`](./plugins/git-assistant)
- [`plugins/code-review`](./plugins/code-review)
- [`plugins/slim-agents-md`](./plugins/slim-agents-md)
- [`plugins/ui-design`](./plugins/ui-design)

## 參考

- [Claude Code Plugins](https://docs.anthropic.com/en/docs/claude-code/plugins)
- [Codex Agent Skills](https://github.com/openai/skills)
- [Pi Packages](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/packages.md)

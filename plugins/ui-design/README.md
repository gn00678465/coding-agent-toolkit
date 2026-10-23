# ui-design

`impeccable-ui-designer` 是一個 UI 設計 subagent，搭配 `ui-design` skill 自動觸發。它以 [agency-agents 的 design-ui-designer](https://github.com/msitarzewski/agency-agents/blob/main/design/design-ui-designer.md) 為角色基礎，設計方法全部改由 [impeccable](https://github.com/pbakaus/impeccable) skill 執行，包括 context 載入、visitor mode、craft floor、detector 與 bounded verification。

## 與原版 design-ui-designer 的差異

| 項目 | design-ui-designer | impeccable-ui-designer |
|------|--------------------|------------------------|
| 設計方法 | 依模型內建的知識 | 一律先載入 impeccable skill；skill 不存在時回報 `SKILL_MISSING`，不改用通用預設 |
| Design system | 先建立 token 範本（Inter、藍色主色、卡片 hover 位移） | 先用 `init` 寫 PRODUCT.md，第一個頁面定稿後再 `extract` 與 `document` 產出 DESIGN.md；需要先鎖定方向時用 `document --seed` |
| 路由 | 無 | 依固定順序的決策樹選指令：沒有設計 → `init` → new-work；只想看畫面 → 建議在主 session 跑 `live` / `generate`；審查 → `critique` / `audit`；局部調整 → 對應的 refine 指令 |
| 版面野心 | 所有介面採同一套標準 | 依 visitor mode（Persuade / Experience / Operate / Read）與 platform 調整 |
| 無障礙 | 從構思階段就以 WCAG AA 為前提 | 對比、焦點、鍵盤、reduced motion 由 craft floor 確保；完整審查交給 `audit`，避免為了保守而讓設計變平庸 |
| 驗證 | 未限制次數的 design QA | 每次建構只做一次多視窗批次檢查與修復，最多再確認一次 |
| 互動 | 無 | 遇到需要使用者決定的關卡時，在寫入任何檔案前回傳 `NEEDS_DECISION`，不自行推論答案；`live` / `generate` 建議交由主 session 執行 |
| 交付 | 無 | 最後一則訊息必須是完整報告，等 impeccable 的子 agent 跑完才回傳；不在建構時順便寫 DESIGN.md；最後一次寫入後再跑 detector；不寫入專案目錄外的路徑 |

## 前置需求

impeccable skill 需能被 agent 載入，安裝方式擇一：

```bash
npx impeccable install --providers=claude,codex
```

```text
/plugin install impeccable@coding-agent-toolkit
```

## 檔案結構

```text
plugins/ui-design/
├── .apm/agents/impeccable-ui-designer.agent.md   # agent 原始檔
├── .apm/skills/ui-design/                        # 觸發 agent 的 skill 原始檔
├── .claude/agents/impeccable-ui-designer.md      # apm-go 產生（Claude Code 專案層級）
├── .codex/agents/impeccable-ui-designer.toml     # apm-go 產生（Codex）
├── .claude/skills/ui-design/                     # apm-go 產生（Claude Code）
├── .agents/skills/ui-design/                     # apm-go 產生（Codex）
├── apm.yml                                       # targets: claude, codex
└── apm.lock.yaml
```

只修改 `.apm/` 底下的原始檔，然後重新產生：

```bash
cd plugins/ui-design
apm-go install
```

apm-go 會把原始檔原樣複製為 Claude Code 的 agent，並轉成 Codex 的 TOML。Codex 版只保留 `name`、`description` 與 `developer_instructions`。

## 安裝

**Claude Code**：plugin 透過 `.claude-plugin/plugin.json` 的 `agents` 欄位直接載入原始檔 `.apm/agents/impeccable-ui-designer.agent.md`，agent 名稱為 `ui-design:impeccable-ui-designer`。這個欄位不指向 `.claude/agents/` 底下產生的檔案，因為那樣 apm-go 安裝時會把同一個 agent 讀兩次，並出現「1 file skipped」警告。

```text
/plugin install ui-design@coding-agent-toolkit
```

**Codex**：Codex plugin 不會載入 subagent，請把 agent 部署到專案的 `.codex/agents/`。

```bash
# 在目標專案中，用 apm-go 安裝（同時部署 Claude Code 與 Codex 的 agent）
apm-go install gn00678465/coding-agent-toolkit/plugins/ui-design --target claude,codex

# 或直接複製
cp plugins/ui-design/.codex/agents/impeccable-ui-designer.toml <project>/.codex/agents/
```

## 使用

直接描述 UI 需求即可，例如「settings.html 的表單太擠了，幫我把間距調整好」。`ui-design` skill 會自動觸發，流程如下：

1. 主 session 載入 `ui-design`，把需求原文整理成 brief，交給 `impeccable-ui-designer`（Claude Code 用 Agent tool，Codex 用 `spawn_agent`）。
2. subagent 回報 `NEEDS_DECISION` 時，主 session 把問題轉給你（Claude Code 用 AskUserQuestion），再把答案交回同一個 subagent。
3. 回報 `DONE` 時，主 session 摘要變更、設計決策、驗證結果與 waiver，並提供下一步。
4. 要看即時變體時，主 session 和你一起執行 `/impeccable live` 或 `/impeccable generate`，subagent 不會自己啟動。

也可以手動指定：Claude Code 說 `Use the impeccable-ui-designer agent to ...`，Codex 說 `$ui-design ...`。Pi 沒有 subagent，`ui-design` 會改用 inline 模式：在主 session 讀取 agent 定義並照著執行，需要決定時直接問你。Pi 的安裝方式見根目錄 README 的「Pi 安裝方式」。

agent 結束時會回傳固定格式的報告，內容包含狀態、route、mode、platform、變更檔案、設計決策、驗證結果、waiver、context 通知與下一步建議。

## 授權

本 plugin 採 MIT 授權。角色內容改寫自 agency-agents（MIT，Copyright (c) 2025 AgentLand Contributors），授權全文見 [upstream LICENSE](https://github.com/msitarzewski/agency-agents/blob/4e3ac3ca6604c75113f52c695dbddcc7af928b46/LICENSE)。impeccable（Apache-2.0）不隨本 plugin 散布，agent 只在執行時引用使用者自行安裝的 skill。

# 研究筆記：為 coding-agent-toolkit 設計 Skill Router（精準技能選擇）

- **主要來源**：
  - Claude Code 官方文件 [`code.claude.com/docs/en/skills`](https://code.claude.com/docs/en/skills)、[`.../en/plugins`](https://code.claude.com/docs/en/plugins)、[`.../en/memory`](https://code.claude.com/docs/en/memory)、[`.../en/hooks`](https://code.claude.com/docs/en/hooks)、[`.../en/plugins-reference`](https://code.claude.com/docs/en/plugins-reference)
  - Agent Skills 開放規格 [`agentskills.io`](https://agentskills.io)、[`agentskills.io/specification`](https://agentskills.io/specification)
  - Codex 官方文件（`developers.openai.com/codex/skills` 308 導向至 [`learn.chatgpt.com/docs/build-skills`](https://learn.chatgpt.com/docs/build-skills)）與 [`openai/codex` repo 的 `docs/skills.md`](https://github.com/openai/codex/blob/main/docs/skills.md)
  - OpenCode 官方文件 [`opencode.ai/docs/skills/`](https://opencode.ai/docs/skills/)
  - 本機 `~/.claude/skills/` 下已安裝的 router 型 skill 原始檔（`opencli-usage`、`spk-start-here`、`spk-meta-skill-map`、`spk-start-command-map`、`gitnexus-guide`）
  - 本 repo 目前分支（`feat/add-external-marketplace-packages`）鎖定的 7 個外部套件，在 `apm.yml` 記錄的 pinned commit sha 上，以 `gh api repos/<owner>/<repo>/contents/...?ref=<sha>` 直接讀取的 `SKILL.md` 原始內容
  - 本 repo 4 個 in-house 插件（`git-assistant`、`advisor`、`code-review`、`slim-agents-md`）的 `SKILL.md`
- **延伸引用**：`anthropics/skills` repo 的 `template/SKILL.md`（描述欄位的最小範例）
- **檢索備註**：
  - `claude plugin eval` 與 `/skill-doctor` 兩者皆**查無官方文件記載**——`code.claude.com/docs/en/plugins-reference` 僅記載 `claude plugin validate`（檢查 manifest schema 與 agent frontmatter 是否可解析），未提及任何測量 skill 觸發準確度的 CLI 指令或 `/skill-doctor` 指令。與「測量 skill 觸發」最接近、且**確實有文件記載**的機制是 `code.claude.com/docs/en/skills` 中的 `skill-creator` 官方外掛（`/plugin install skill-creator@claude-plugins-official`）搭配的 eval 流程（`evals/evals.json` → `benchmark.json`/`grading.json`），細節見下第 1.1.5 節。
  - `npx ctx7@latest library "Claude Code" ...` 依使用者全域規則本應優先於官方文件站，但本次研究改採直接讀取 `code.claude.com/docs` 頁面（`WebFetch`）取得等量或更完整的一手資料，故未額外呼叫 ctx7；此為程序上的偏離，特此註記。
  - OpenCode 官方 repo（`sst/opencode`）以 GitHub code search 查詢 `skill.ts` / `SKILL.md` 路徑無回傳結果（API 限制或索引延遲），故 OpenCode 一節僅以官方文件站內容為準，未能交叉核對原始碼實作。
  - taste-skill、beautify-github-readme 等套件的 `README.md`、`LICENSE` 等非 `SKILL.md` 內容未逐一深讀，僅讀取路由分析所需的 `SKILL.md` 檔案。
- **檔案位置說明**：延續 `docs/research/agents-md-refactoring.md` 建立的 `docs/research/` 慣例，本檔案為第二篇研究筆記。

---

## 1. 三個 host 實際如何選擇 skill

### 1.1 Claude Code

#### 1.1.1 SKILL.md frontmatter 完整欄位語意（文件明載）

`code.claude.com/docs/en/skills` 的 frontmatter 參照表列出以下與路由直接相關的欄位（來源：`code.claude.com/docs/en/skills`）：

| 欄位 | 語意 |
|---|---|
| `name` | 「Display name shown in skill listings. Defaults to the directory name.」——不設定時預設用資料夾名稱。 |
| `description` | 「What the skill does and when to use it. **Claude uses this to decide when to apply the skill.**」若省略則退回使用 markdown 內文第一段。 |
| `when_to_use` | 「Additional context for when Claude should invoke the skill, such as trigger phrases or example requests.」**附加**在 `description` 之後，一起計入同一個字元上限。 |
| `argument-hint` | 純粹是 autocomplete 時顯示的參數提示，例如 `[issue-number]`，**不影響**模型是否觸發該 skill。 |
| `disable-model-invocation` | 設為 `true` 時「prevent Claude from automatically loading this skill」——只能用 `/name` 手動叫用；同時也會讓該 skill 不會被 preload 進 subagent、不會被排程任務觸發。 |
| `user-invocable` | 設為 `false` 時「only Claude can invoke the skill」——會從 `/` 選單隱藏、打 `/name` 也不會執行；適合「背景知識」型 skill。 |
| `allowed-tools` / `disallowed-tools` | 只在**該 skill 被觸發的那個 turn**內生效的工具權限，下一則訊息就失效；**不影響**模型「是否」選擇這個 skill，只影響選中之後能不能免確認呼叫工具。 |
| `paths` | 「Glob patterns that limit when this skill is activated. ... Claude loads the skill automatically only when working with files matching the patterns.」——唯一一個**依檔案路徑**而非語意描述來限制自動觸發範圍的欄位。 |

（來源：`code.claude.com/docs/en/skills` frontmatter 參照表）

**關鍵結論**：Claude Code 用來判斷「這次要不要用這個 skill」的觸發面，只有 `description` + `when_to_use` 兩個欄位拼接後的文字（以及選配的 `paths` 檔案過濾）。`argument-hint`、`allowed-tools` 等欄位對「選不選中」完全沒有影響，只影響選中之後的行為——這是本研究判斷「哪個欄位才是路由的槓桿」的直接依據。

#### 1.1.2 描述如何變成「觸發面」：字元上限與 context 預算（文件明載，數字精確）

- 「Put the key use case first: the combined `description` and `when_to_use` text is **truncated at 1,536 characters** in the skill listing to reduce context usage.」（`description` 可配置：`skillListingMaxDescChars`）（來源：`code.claude.com/docs/en/skills`）
- Claude Code 會把「所有 skill 的 name + description」整理成一份 listing 放進 context，讓 Claude 決定要不要用哪一個：「Claude Code loads a listing of skill names and descriptions into context so Claude knows what's available. The listing always contains every skill name, but if you have many skills, Claude Code shortens descriptions to fit the listing's character budget... **The budget scales at 1% of the model's context window.** When the listing overflows, Claude Code drops descriptions starting with the skills you invoke least, so the skills you use most keep their full text.」（可配置：`skillListingBudgetFraction`，例如 `0.02` = 2%）（來源：`code.claude.com/docs/en/skills`，「Skill descriptions are cut short」段落）
- 對照 Agent Skills 開放規格自身的 progressive disclosure 三階段：「1. **Metadata** (~100 tokens): the `name` and `description` fields are loaded at startup for all skills. 2. **Instructions** (< 5000 tokens recommended): the full `SKILL.md` body is loaded when the skill is activated. 3. **Resources**: as needed.」（來源：`agentskills.io/specification`）——這解釋了為什麼「本體」多長都不太要緊，但 `description` 本身的字數是**每個 skill 都要付出的固定稅**，skill 數量一多，這筆稅就會排擠彼此。

**與本研究直接相關的量化推論（推論，非文件明載的具體數字，但方法論引用自文件機制）**：本 repo 目前鎖定的 7 個外部套件實際展開後共 26 個獨立 skill 單元（見第 3 節逐一清點），加上本 repo 自身 6 個 skill，全部啟用後約 32 個 skill 同時競爭同一份 listing 的字元預算。依上述機制，一旦超出預算，Claude Code 會「從最少被呼叫的 skill 開始砍描述」（`drops descriptions starting with the skills you invoke least`）——也就是說，即使某個冷門但語意精準的 skill（例如 `web-quality-skills` 底下的 `core-web-vitals`）在使用者第一次真正需要它時，因為過去很少被叫用、描述可能已被砍短，反而更不容易被選中。這是本研究認為「單靠 32 條描述互相競爭」不可長期依賴、需要 router 介入的量化依據。

#### 1.1.3 `user-invocable` / `disable-model-invocation` 兩軸矩陣（文件明載）

| | Claude 可自動觸發 | 使用者可 `/name` 觸發 |
|---|---|---|
| `disable-model-invocation: true` | 否 | 是（description 不進 context，叫用時才載入全文） |
| `user-invocable: false` | 是（description 常駐 context） | 否 |

（來源：`code.claude.com/docs/en/skills`「Control who invokes a skill」表格）

另有 **`skillOverrides`** 設定（放在 `settings.json`，不需要改 skill 自己的 frontmatter，「Use it for skills whose SKILL.md you don't want to edit, such as ones checked into a shared project repo」）四種狀態：

> **限制（文件明載，對本研究極關鍵）**：「**Plugin skills are not affected by `skillOverrides`. Manage those through `/plugin` instead.**」而 `/plugin` 能做的只有整個插件的 enable／disable／uninstall（「Plugin skill: disable or uninstall the plugin that provides it, from the `/plugin` menu」）——**無法對插件內的單一 skill 做 name-only／off**。本 repo 的 7 個外部套件與 4 個 in-house 插件全部是 plugin skill，因此 `skillOverrides` 對本研究的所有對象**一律無效**；下列四狀態僅適用於 personal／project／bundled skill（來源：`code.claude.com/docs/en/skills`「Override skill visibility from settings」「Disable a skill」）。


| 值 | 對 Claude 是否可見 | 是否出現在 `/` 選單 |
|---|---|---|
| `"on"`（預設） | 名稱＋描述 | 是 |
| `"name-only"` | 只有名稱 | 是 |
| `"user-invocable-only"` | 隱藏 | 是 |
| `"off"` | 隱藏 | 隱藏 |

（來源：`code.claude.com/docs/en/skills`「Override skill visibility from settings」）

**這一點對本研究極其關鍵**：本 repo 的 7 個外部套件是以 `ref`/`sha` 鎖定、不可編輯其 `SKILL.md` 的（見第 3 節、以及 `README.md` 明文：「本專案不散布這些套件的程式碼...marketplace 僅保存 URL 與 commit sha 指標」）。但 `skillOverrides` 是**唯一不需要改到 pinned 檔案本身、就能改變其路由行為**的官方機制——可以把明顯多餘或高風險誤觸發的子 skill（例如 taste-skill 的舊版 `design-taste-frontend-v1`）設成 `"name-only"` 或 `"off"`，直接降低 listing 預算的競爭者數量。這是第 5 節設計方案會採用的具體槓桿之一。

#### 1.1.4 Skill 內容生命週期與 compaction（文件明載，與「router 之後還要不要重新觸發」有關）

「When you or Claude invoke a skill, the rendered `SKILL.md` content enters the conversation as a single message and stays there across later turns... Claude Code does not re-read the skill file on later turns.」「Auto-compaction carries invoked skills forward within a token budget... re-attaches the most recent invocation of each skill after the summary, keeping the first 5,000 tokens of each. Re-attached skills share a combined budget of 25,000 tokens.」（來源：`code.claude.com/docs/en/skills`「Skill content lifecycle」）——意味著 router skill 本身若被觸發，其內容也會佔用這筆固定 25,000 token 的 compaction 預算，router 應盡量精簡（見第 5 節「router 本身要小」的設計原則）。

#### 1.1.5 Skill 觸發準確度的官方評測機制：`skill-creator`（文件明載，並非 `claude plugin eval` 或 `/skill-doctor`）

官方文件描述的評測方法是**基準比較（baseline comparison）**：「Collect a few realistic prompts, run each one in a fresh session with the skill available and again with it disabled, and compare the results.」並提供官方外掛 `skill-creator`（`/plugin install skill-creator@claude-plugins-official`）自動化這個迴圈，內容包含：

- **Isolated runs**：每個測試案例都在獨立 subagent 執行，避免 context 污染
- **Benchmark**：把「有 skill / 沒 skill」的通過率、時間、token 數彙整進 `benchmark.json`
- **Description tuning**：「generates should-trigger and should-not-trigger prompts, measures the hit rate, and proposes description edits when the skill activates on the wrong requests」——這正是本研究要解決的「跨套件誤觸發」問題官方給的對應工具，但**只對自己能編輯 `SKILL.md` 的 skill 有用**（例如本 repo 自己的 4 個 in-house 插件），對 pinned 的 7 個外部套件無法直接套用。

（來源：`code.claude.com/docs/en/skills`「Evaluate and iterate on a skill」）

#### 1.1.6 Plugin skill 命名空間（文件明載）

「Plugin skills use a `plugin-name:skill-name` namespace, so they can't conflict with other levels.」例如 `my-plugin/skills/deploy/SKILL.md` 變成 `/my-plugin:deploy`（來源：`code.claude.com/docs/en/skills`「Where skills live」）。命名空間只解決**同名衝突**（例如未來若某外部套件也叫 `deploy`，不會跟另一個外部套件的 `deploy` 衝突），但**完全不解決語意重疊**——`impeccable` 與 `taste-skill:taste-skill` 命名空間不同、不會「衝突」，但它們的 `description` 觸發面幾乎完全重疊，這是本研究第 3 節分析的重點，命名空間機制對此無能為力。

**識別名的實際形態（使用者實測，非文件逐字明載）**：
- **識別名 = `plugin-name:<skill 目錄名>`，slash 形態亦含命名空間前綴**。實測 `taste-skill` 插件的 slash command 為 `/taste-skill:taste-skill` 與 `/taste-skill:taste-skill-v1`——用的是目錄名 `skills/taste-skill/`、`skills/taste-skill-v1/`，**不是** frontmatter `name` 的 `design-taste-frontend`／`design-taste-frontend-v1`。單一 skill 的插件因此會出現 `archify:archify` 這種「插件名:同名目錄」的重複形態。
- 模型看到的 skill listing 用的是同一套識別名（本研究於 Claude Code session 內確認 listing 形態為 `git-assistant:commit-message`、`security-supply-chain:security-supply-chain` 等 `plugin:dir` 形態；`Skill` tool 亦要求傳入「exact name from the listing」）。
- 文件對 `name` 欄位的定義「Display name shown in skill listings. Defaults to the directory name.」在此情境下應理解為**顯示用途**；實際的呼叫識別名以目錄名為準（推論：由實測結果反推文件語意；`taste-skill` 是本 repo 唯一目錄名 ≠ `name` 的套件，共 13 個 skill 中 10 個不一致，其餘六個套件不受影響）。
- 對 router 的意義：決策表一律引用 `plugin:目錄名`，例如 `taste-skill:brutalist-skill`，而非以 frontmatter `name` 組成的 `taste-skill:industrial-brutalist-ui`。

#### 1.1.7 `UserPromptSubmit` hook 與 `.claude/rules/`：能否影響路由（文件明載，結論為「不能」）

- `UserPromptSubmit` hook 在「Claude 開始處理 prompt 之前」觸發，能做的事包括：透過 `additionalContext` 附加文字給 Claude、透過 `updatedInput` 修改 prompt 本文、或用 exit code 2 直接擋掉整個 prompt。**Claude Code 官方文件沒有把它描述為 skill 選擇/路由機制**——它運作在「原始 prompt 文字」層級，發生在任何 skill 展開或指令解析**之前**（來源：`code.claude.com/docs/en/hooks`）。
  - **推論**：技術上仍可以自己寫一個 `UserPromptSubmit` hook，用關鍵字比對使用者輸入，透過 `additionalContext` 塞入一句「偵測到設計相關字眼，請優先考慮 X skill」，間接影響 Claude 的選擇。但這需要自己維護一套關鍵字規則、且**只在 Claude Code 有 hook 這個機制**（Codex 官方文件未提及對等機制、OpenCode 文件也未提及）——不是一個可攜的解法，且關鍵字比對在語意匹配能力上天生弱於模型直接讀 `description` 做語意判斷。此為推論，非文件建議的用法。
- `.claude/rules/*.md`：官方文件明確說「**Rules load into context every session** or when matching files are opened. For task-specific instructions that don't need to be in context all the time, **use skills instead**, which only load when you invoke them or when Claude determines they're relevant to your prompt.」（來源：`code.claude.com/docs/en/memory`「Organize rules with `.claude/rules/`」提示框）——也就是說，若把一份 11 個套件的路由決策表寫進 `.claude/rules/`（沒有 `paths:` 限定時），它的載入時機跟 `CLAUDE.md` 一樣是**每個 session 都載入**，完全不是 progressive disclosure；這跟 skill 的「只在被選中時才載入本體」正好相反。這一結論與本 repo 既有的 `docs/research/agents-md-refactoring.md`（研究 CLAUDE.md instruction budget、150–200 instructions 上限、token 每次都被載入的代價）完全一致，形成第 5 節否決方案 (b) 的直接依據。

### 1.2 Agent Skills 開放規格（agentskills.io）

- 一比一還原三個 frontmatter 硬性約束（皆為文件明載）：`name` 「Max 64 characters. Lowercase letters, numbers, and hyphens only.」、`description` 「Max 1024 characters. Non-empty.」、`compatibility`（選填）「Max 500 characters.」。（來源：`agentskills.io/specification`）——注意 Claude Code 自己的 1,536 字元上限是**「description + when_to_use 合計」**的 listing 顯示上限，跟規格本身「單一 description 最多 1024 字」是兩個不同層級的限制，不衝突但容易混淆，行文中需區分清楚。
- 對 `description` 撰寫品質給了明確的好壞範例對照：「Poor example: `Helps with PDFs.`」vs 「Good example: 完整列出功能＋『Use when working with PDF documents or when the user mentions PDFs, forms, or document extraction.』」，並指出「Should include specific keywords that help agents identify relevant tasks.」（來源：`agentskills.io/specification`「description field」）——這是本研究後續評判 7 個外部套件描述品質好壞的官方判準來源。
- Progressive disclosure 三階段（Discovery → Activation → Execution）與 Claude Code 文件互相印證，見上第 1.1.2 節引用。
- 規格明文列出 40 個以上採用 Agent Skills 的 client（Claude Code、Codex/ChatGPT、OpenCode、Cursor、GitHub Copilot、VS Code 等），確立這是一個真正的**跨工具開放格式**，而非 Claude Code 專屬（來源：`agentskills.io` client showcase 列表）。

### 1.3 Codex（openai/codex）

- `openai/codex` repo 內 `docs/skills.md` 全文只有一句轉介：「For information about skills, refer to [this documentation](https://developers.openai.com/codex/skills).」（來源：`github.com/openai/codex/blob/main/docs/skills.md`，於 pinned 版本讀取確認）——代表 Codex 的 skills 文件權威來源是 `developers.openai.com/codex/skills`（實際存放於 `learn.chatgpt.com/docs/build-skills`，前者 308 導向後者）。
- Codex 的 `SKILL.md` 必要 frontmatter 只有 `name` 與 `description`，且明確定位 `description` 為觸發邊界：「description: Defines when the skill should/shouldn't trigger」（來源：`learn.chatgpt.com/docs/build-skills`）。額外的 UI/工具依賴設定放在**旁路檔案** `agents/openai.yaml`，不影響觸發——這與本 repo 目前的做法一致（`README.md` 提到「每個 skill 目錄內含 `agents/openai.yaml` 提供 Codex UI 顯示名稱與預設 prompt」）。
- 兩種觸發方式：**顯式**（使用者在 Codex CLI 打 `$skill-name`）與**隱式**（「Codex autonomously selects skills when user prompts match the skill's description」）。掃描路徑依序含 `$CWD/.agents/skills`、repo 上層與根目錄的 `.agents/skills`、`$HOME/.agents/skills`、`/etc/codex/skills`、系統內建 skill（來源：`learn.chatgpt.com/docs/build-skills`）。
- Progressive disclosure 的具體數字與 Claude Code 並列可比：「Codex uses 'progressive disclosure': it loads only skill names and descriptions initially, limiting the skills list to **at most 2% of the model's context window, or 8,000 characters when the context window is unknown**.」（來源：同上）——同一個「listing 預算會排擠彼此」的問題在 Codex 上依然成立，甚至基準預算（2% vs Claude Code 預設 1%）更寬鬆一些，但機制本質相同：**router 策略若只考慮 Claude Code、不考慮 Codex 的這道預算，會在 Codex 平台上重演同樣的問題**（本 repo `apm.yml` 的 `outputs.codex` 目前註解關閉，但已為未來開啟預留欄位）。

### 1.4 OpenCode

- SKILL.md 搜尋路徑：`.opencode/skills/<name>/SKILL.md`、`~/.config/opencode/skills/<name>/SKILL.md`，以及與 Claude 相容的 `.claude/skills/<name>/SKILL.md`（來源：`opencode.ai/docs/skills/`）——這代表 `README.md` 目前教使用者「手動複製 skill 目錄」到 `.opencode/skills/` 的作法（`cp -r plugins/code-review/skills/review-forge .opencode/skills/`）在路徑慣例上是正確的。
- 必要 frontmatter 與規格一致：`name`（1–64 字元、`^[a-z0-9]+(-[a-z0-9]+)*$`）、`description`（1–1024 字元）。
- **選擇機制與 Claude Code 明顯不同**：OpenCode 讓 agent 透過一個原生 `skill` 工具（tool）發現與叫用 skill，「The tool description displays skill names and their descriptions together. Agents invoke skills by calling: `skill({ name: "git-release" })`.」（來源：`opencode.ai/docs/skills/`）。也就是說，OpenCode 沒有像 Claude Code 那樣一份獨立、有預算上限、會自動截斷的「skill listing」——選擇邏輯內嵌在單一工具的描述欄位裡，本次檢索**未找到**任何關於該工具描述本身有無字數上限、或超量時如何降級的說明；此為文件缺口，非「不存在」，僅是**未查得**。
- 權限層面另有一組管理員可配置的 `allow`/`deny`/`ask` 規則（`opencode.json`，支援萬用字元如 `internal-*`），可以在管理層直接隱藏或需要人工核准某些 skill——這與 Claude Code 的 `skillOverrides` 精神類似，但作用對象是「誰能用」而非「模型該不該自動選」。

---

## 2. 既有的 router / meta-skill 命名模式（本機已安裝 skill 的第一手實例）

以下技巧從 `~/.claude/skills/` 下實際安裝的 skill 原始檔逐一讀出，代表「已經在生產環境跑過」的路由寫法，而非憑空設計。

### 2.1 `opencli-usage`：「Where to go next」決策表

自我定位為「the top-level map of what `opencli` can do... and which specialized skill to load next」，本文結尾用一張表收斂路由（來源：`~/.claude/skills/opencli-usage/SKILL.md`）：

```text
| If you're about to…                                              | Load this skill        |
|-------------------------------------------------------------------|-------------------------|
| Drive a live browser ad-hoc (no adapter available, or prototyping)| opencli-browser         |
| Write a new adapter, or add a command to an existing site         | opencli-adapter-author  |
| Fix a broken adapter after a command failure                      | opencli-autofix         |
| Route a search / lookup / research request to the right adapter   | smart-search            |
```

技巧要點：表格放在**檔案最後**（先講清楚 router 自己能做什麼，最後才收斂路由），欄位是「情境（動名詞片語）→ 該載入的 skill 名稱」，而非「skill 名稱 → 描述」——這樣使用者/模型是從「我正要做的事」反查，而不是從一堆 skill 名稱裡面猜。

### 2.2 `spk-start-here`：分層 + 明確 fallback

把系統分成三層（Commands / Skills / Doctrine）先講清楚「這是什麼」，再用「First Route」條列 8 條路由規則，每條都是「情境陳述：use `<skill>`」的固定句型，最後一條明確保底：「Unsure which skill applies: use `spk-meta-skill-map`.」（來源：`~/.claude/skills/spk-start-here/SKILL.md`）。文末「Agent Behavior」一段直接指示模型行為：「State the route, load only the routed skill, and continue... Do not turn this into a full tutorial.」——這解決了「router 講太多變成另一個大 skill」的風險。

### 2.3 `spk-meta-skill-map`：命名慣例即路由線索 + 衝突時的優先序規則

比 `spk-start-here` 更進一步，把「怎麼發現該用哪個 skill」本身系統化：先定義命名慣例 `spk-<family>-<action-or-topic>`（`spk-start-*`、`spk-run-*`、`spk-gate-*`…），讓 skill 名稱本身自帶語意分類；再給一條明確的**衝突裁決規則**：「Choose the narrowest matching skill. **If multiple skills match, start at the earliest lifecycle family**: start, mission, run, gate, admin/team, doctrine, integrate, meta.」（來源：`~/.claude/skills/spk-meta-skill-map/SKILL.md`）——這是本次檢索中**唯一**明確處理「即使 router 表格設計得再好，還是可能兩條規則同時命中」這個殘餘問題的實例，給出了「取最窄匹配；仍打平時按生命週期順序」的確定性 tie-break 邏輯，比單純的表格更進一步。

### 2.4 `spk-start-command-map`：邊界聲明（命令 vs 操作指南）

「Route command questions without conflating command wrappers and operating skills.」明確區分「`/spec-kitty.*` 是可執行的命令介面」與「`spk-*` 是給 agent 看的操作指南」，並在文末用一段「Boundary」把兩者的差異寫死，避免使用者或模型把兩種完全不同性質的東西混為一談（來源：`~/.claude/skills/spk-start-command-map/SKILL.md`）。

### 2.5 `gitnexus-guide`：任務類型表 + 「先讀活資源、再查表」的原則

「## Always Start Here」段落先要求讀一個**即時**資源（`gitnexus://repo/{name}/context`，含 index 新鮮度檢查），再用「Task → Skill to read」表格收斂路由；表格之後緊跟一句「Follow the skill's workflow and checklist」（來源：`~/.claude/skills/gitnexus-guide/SKILL.md`）。技巧要點：路由表本身很短（6 行），大部分篇幅留給「如果選錯了，之後真正要用的工具長什麼樣子」的參考資料——這符合 progressive disclosure 精神：router 只需要精準地把使用者送到下一步，不需要在 router 裡把下游知識也講一遍。

### 2.6 分散式路由：套件內部用 negative trigger 自我消歧（來自本 repo 已鎖定的 `reviewable-html-workbench`）

與上述「集中式 router skill」不同的另一種模式是**把消歧責任下放到每個 leaf skill 的 `description` 本身**。`reviewable-html-workbench` 的 3 個 skill（`plan-preview`、`reviewable-design-doc`、`visual-html-renderer`）彼此的 `description` 都用雙語（日文＋英文）明確列出「使用しない場面 / Do not use for:」，逐一點名不該用自己、該用哪個手足 skill，細節見第 3.6 節。這種寫法只有在**能編輯 `SKILL.md` 本身**時才可行（本 repo 自己的 4 個 in-house 插件可以這樣做，7 個 pinned 外部套件不行）。

---

## 3. 本 repo 7 個外部套件的真實觸發面（讀自 pinned sha 的 `SKILL.md`）

以下描述皆逐字讀自 `apm.yml` 記錄的 pinned commit sha，未經改寫。**重要發現**：`apm.yml` 上寫的「7 個套件」，實際展開後是 **26 個獨立 skill 單元**——因為 marketplace 條目多數指向整個 `skills/` 目錄，而不是單一 skill。

### 3.1 `web-quality-skills`（6 個 skill，`category: Productivity`）

無 `subdir`，`skills/` 下 6 個 skill 全部隨套件安裝：`accessibility`、`best-practices`、`core-web-vitals`、`performance`、`seo`、`web-quality-audit`。每個都用「Use when asked to "X", "Y", or "Z"」的引號觸發詞句型（例如 `accessibility`：「Use when asked to "improve accessibility", "a11y audit", "WCAG compliance", "keyboard navigation", or "make accessible".」）。`web-quality-audit` 本身即是這 6 個之中的「總入口」：「Run an evidence-led web quality audit covering performance, accessibility, SEO, best practices, and agentic browsing.」——與其餘 5 個個別領域 skill 的描述**完全重疊**（一個籠統的「幫我看看我的網站」請求，6 個 skill 全部語意命中）。此套件內部**沒有**寫任何 negative trigger 互相排除，路由完全依賴使用者措辭的精確度。

### 3.2 `impeccable`（1 個 skill，但源碼是模板 `SKILL.src.md`，`category: design`）

```yaml
name: impeccable
description: "Use when the user wants to design, redesign, shape, critique, audit,
  polish, clarify, distill, harden, optimize, adapt, animate, colorize, extract,
  or otherwise improve a frontend interface. Covers websites, landing pages,
  dashboards, product UI, app shells, components, forms, settings, onboarding,
  and empty states. Handles UX review, visual hierarchy, information architecture,
  cognitive load, accessibility, performance, responsive behavior, theming,
  anti-patterns, typography, fonts, spacing, layout, alignment, color, motion,
  micro-interactions, UX copy, error states, edge cases, i18n, and reusable
  design systems or tokens. ... Not for backend-only or non-UI tasks."
argument-hint: "[{{command_hint}}] [target]"
user-invocable: true
allowed-tools:
  - Bash(npx impeccable *)
  - Bash(node {{scripts_path}}/*)
license: Apache 2.0
```

（來源：`pbakaus/impeccable` repo `skill/SKILL.src.md`，`ref=63b04e2530f5c7b41ea83c133daab24f34912456`）

**觀察（非最終結論，因讀到的是模板源檔）**：檔名為 `SKILL.src.md` 且內文含 `{{command_hint}}`、`{{scripts_path}}` 佔位符，代表上游有自己的建置流程把模板渲染成最終的 `SKILL.md`；本研究讀到的是安裝前的模板，實際 pinned sha 安裝後的確切最終文字（尤其 `description` 是否在渲染階段被改寫）未逐一核對建置腳本，此處視為**近似值**。即使如此，`description` 動詞列表（design/redesign/shape/critique/audit/polish...）與涵蓋範圍（websites、dashboards、product UI、forms...）本身已足以說明其觸發面極廣，是三個「design」套件中範圍最大、唯一明確涵蓋 dashboard/product UI 的一個。

### 3.3 `taste-skill`（13 個 skill，無 `subdir`，`category: design`——套件內部語意重疊最嚴重的一組）

`skills/` 下全部 13 個資料夾都隨套件安裝：`taste-skill`（v2、預設）、`taste-skill-v1`、`redesign-skill`、`brutalist-skill`、`minimalist-skill`、`soft-skill`、`brandkit`、`output-skill`、`stitch-skill`、`image-to-code-skill`、`imagegen-frontend-mobile`、`imagegen-frontend-web`、`gpt-tasteskill`。重點摘要：

| 資料夾 | frontmatter `name` | 觸發要點 |
|---|---|---|
| `taste-skill`（v2 預設） | `design-taste-frontend` | 「Anti-slop frontend skill for **landing pages, portfolios, and redesigns**.」正文明確排除：「Not dashboards, not data tables, not multi-step product UI.」——這是本套件**唯一**寫了明確 negative trigger 的一個。 |
| `taste-skill-v1` | `design-taste-frontend-v1` | 「preserved for projects depending on its exact behavior... Use this v1 install name **only if you need exact backward compatibility**.」——本質是舊版相容殼，但仍會出現在 listing 裡跟其他 12 個一起競爭。 |
| `redesign-skill` | `redesign-existing-projects` | 「Upgrades existing websites and apps to premium quality. Audits current design, identifies generic AI patterns...」——與 `impeccable` 的 audit/redesign 觸發詞高度重疊，也與 `taste-skill` 本尊的「redesigns」重疊。 |
| `brutalist-skill` / `minimalist-skill` / `soft-skill` / `gpt-tasteskill` | 各自風格化命名 | 四個都是「特定美學流派」的實作指南（工業感/極簡/高端質感/GSAP 動效），描述本身**沒有互斥語句**，一個籠統的「幫我做一個很有質感的頁面」請求會同時命中全部 4 個，需要使用者自己講出風格關鍵字（brutalist/minimalist 等）才能收斂。 |
| `brandkit` | `brandkit` | 專注品牌識別「圖像生成」（logo、識別系統簡報），不寫程式碼。 |
| `image-to-code-skill` / `imagegen-frontend-mobile` / `imagegen-frontend-web` | 各自命名 | 三者都圍繞「先生圖、再依圖實作/僅生圖」，`image-to-code` 明確標註「For Codex」，`imagegen-frontend-mobile`／`imagegen-frontend-web` 明確聲明「This skill generates images only. It does not write code.」——這組彼此之間**有**寫清楚邊界（誰寫程式碼、誰只生圖），是本套件內部消歧做得較好的一小群。 |
| `output-skill` | `full-output-enforcement` | 與「設計」無關，是「禁止輸出截斷/佔位符」的通用行為覆寫，語意上完全獨立，但因為在同一個套件裡，仍會出現在同一份 listing 中稀釋預算。 |
| `stitch-skill` | `stitch-design-taste` | 專為 Google Stitch 產生 `DESIGN.md`，工具限定明確，重疊面較小。 |

（來源：`Leonxlnx/taste-skill` repo，`ref=ccbc15639c97057cbfcf32ecebc38ef716e4bb37`，逐一讀取各 `skills/*/SKILL.md` frontmatter）

### 3.4 `beautify-github-readme`（1 個 skill，`category: design`）

「Redesign GitHub README homepages or create project-native pure SVG, hybrid SVG-composed PNG/WebP, and opt-in animated GIF assets. Use when a user asks to beautify, redesign, rebrand, visually upgrade, simplify, or audit a GitHub README...」（來源：`oil-oil/beautify-github-readme` repo，`ref=55bdb1c05414cd7a0cf911d02e55ece79777206e`）。範圍限定在 README／repo 首頁視覺資產，是三個 design 套件中觸發面**最窄、最精準**的一個，但 `redesign`、`visually upgrade`、`audit` 這幾個詞跟 `impeccable`／`taste-skill:redesign-skill` 的觸發詞完全重疊，差別只在受詞是「README」還是「UI/frontend」——當使用者說「幫我把這個專案弄好看一點」而沒指名是 README 還是網站介面時，三個套件語意上都算命中。

### 3.5 `show-me`（1 個 skill，`subdir: plugins/show-me`，`category: Productivity`）

「Help the user understand the current topic visually with concise diagrams, code-shape sketches, and focused HTML artifacts.」（來源：`humanlayer/skills` repo，`ref=3c2629142c5d437428269b1b722b08c0b87f574d`）。這是三個「視覺化／可審閱文件」套件中描述**最短、最不設限**的一個——沒有寫任何 non-goal，涵蓋「pseudocode／call tree／component tree／HTML artifacts」等多種形式，等於是把「畫圖說明」這整個語意空間全部認領。

### 3.6 `reviewable-html-workbench`（3 個 skill，無 `subdir`，`category: Productivity`）

三個 skill 彼此用雙語（日文＋英文）明確互相排除，是本次檢索中**套件內部消歧寫得最完整**的範例：

- `plan-preview`：「Triggers: ... graphical plan review, this plan as HTML, ... 使用しない場面: 通常の最終HTML生成、レビュー可能な設計資料作成、... Do not use for: final HTML artifacts, reviewable design docs, comment ingestion, permanent publication...」——明確點名不要跟 `visual-html-renderer`、`reviewable-design-doc` 搶。
- `reviewable-design-doc`：「使用しない場面: 汎用HTMLレンダリングだけ、Notion投稿だけ、既存HTMLの見た目修正だけ。Do not use for: generic HTML rendering, Notion-only publishing, or small visual tweaks to existing HTML.」——正文並直接說明分工：「Final HTML rendering is delegated to `visual-html-renderer`.」
- `visual-html-renderer`：「使用しない場面: Plan Mode 中の計画確認プレビュー、設計内容そのものの作成... Do not use for: Plan Mode proposal previews, creating the design content itself...」——正文自述定位：「Use this shared renderer for HTML-output workflows. It replaces one-off HTML generation logic...」

（來源：`u-ichi/reviewable-html-workbench` repo，`ref=2be05dbd31510670af04381e24d735c4c77493b8`）

三者合起來構成一個「共用 renderer + 兩個各自負責輸入語意的上層 skill」的分工架構，`plan-preview` 與 `reviewable-design-doc` 都會呼叫 `visual-html-renderer` 完成最終輸出，彼此的 `description` 互相標註「這不是我，是隔壁那個」——這是第 5 節推薦方案會直接借用的寫法。

### 3.7 `archify`（1 個 skill，`subdir: archify`，`category: Productivity`）

「Create polished, validated architecture, workflow, sequence, data-flow, and lifecycle/state diagrams as explorable standalone HTML with inline SVG... Use when the user asks to visualize system architecture, infrastructure, cloud/security/network topology, technical workflows, API call sequences, request lifecycles, data pipelines, ETL/ELT, data lineage, state machines, or to convert/beautify Mermaid.」（來源：`tt-a1i/archify` repo，`ref=c826e6c3a7abad19c0f3cd1ca57207d54b1ad8de`）。正文內建一個「Type router」表格（`architecture`/`workflow`/`sequence`/`dataflow`/`lifecycle` 五選一），是**套件內部**（而非套件之間）路由的例子，技巧與第 2 節本機 router 相同（情境 → 選項的表格），但範疇只到「哪一種圖」，不解決「該不該用 archify，還是用 show-me / reviewable-html-workbench」這個更上層的問題。

### 3.8 跨套件衝突矩陣與具體範例 prompt

| 使用者 prompt（範例） | 可能命中 | 衝突原因 |
|---|---|---|
| 「幫我把這個 landing page 重新設計得更高級」 | `impeccable`、`taste-skill`（v2 預設）、`taste-skill:redesign-skill`、`taste-skill:soft-skill`、`taste-skill:gpt-tasteskill` | `impeccable` 的 redesign/polish 觸發詞、`taste-skill` 本尊明講「landing pages... redesigns」、`redesign-skill` 明講「Upgrades existing websites... to premium quality」、`soft-skill`／`gpt-tasteskill` 都主打「高端/awwwards 等級」——五個 skill 語意上全部命中，且彼此**沒有**互相排除的措辭。 |
| 「把我的 GitHub README 弄得好看一點」 | `beautify-github-readme`（精準命中）、`impeccable`（「polish...visual」不限受詞）、`taste-skill:brandkit`（若使用者提到品牌識別） | `beautify-github-readme` 是唯一為此場景設計的，但另外兩個套件的觸發詞沒有排除「README」這種非傳統 UI 的受詞。 |
| 「幫我畫一個系統架構圖」 | `archify`（精準命中）、`show-me`、`reviewable-html-workbench:visual-html-renderer` | `archify` 明確列出 architecture/infrastructure/topology；`show-me` 描述完全不設限（「diagrams... focused HTML artifacts」）；`visual-html-renderer` 明確含「diagrammed HTML report」。三者都輸出 HTML，差別在正式度（`archify` 有驗證/交付/視覺回歸檢查流程，`show-me` 是輕量即興說明）。 |
| 「把這份技術方案整理成可以在瀏覽器上留言討論的文件」 | `reviewable-html-workbench:reviewable-design-doc`（精準命中） | 此套件內部已用 negative trigger 把 `show-me`、`archify` 的常見場景排除在自己描述之外，但反過來 `show-me`／`archify` 的描述**沒有**排除「設計文件」這個場景，理論上仍可能被選中（誤觸發機率較低，因為兩者措辭確實偏向圖表而非文件審閱，但邊界並非文件明載）。 |
| 「review 一下這次改動」 | 本 repo 自身 `code-review:review-forge`、`code-review:verification-gate` | 屬 in-house 衝突（見第 4 節），已由 `verification-gate` 自己的描述排除：「Not a code review skill — it does not read code looking for defects.」——這是本 repo 目前**唯一**已經做到「描述層級互斥」的例子。 |

---

## 4. 本 repo 自身 4 個 in-house 插件的觸發面

| 插件:skill | 觸發面摘要 | 消歧手法 |
|---|---|---|
| `git-assistant:commit-message` | 中文條列「使用時機包括：(1)...(2)...(3)...(4)...」並列出雙語觸發詞清單「commit this」「create a commit」「幫我寫 commit message」「產生 commit」「建立 branch」等（來源：`plugins/git-assistant/skills/commit-message/SKILL.md`） | **明確觸發詞列表**——本 repo 既有的、也是本研究第 5 節建議沿用的手法之一。 |
| `git-assistant:pull-request` | 「應在以下情況立即使用：使用者提到建立/開 PR、open a PR...」並明確聲明範圍外：「不適用於純 git push、git merge、PR code review/審查程式碼（由獨立 review skill 處理）或非 GitHub 平台的 PR 操作。」（來源：`plugins/git-assistant/skills/pull-request/SKILL.md`） | **正向觸發詞 ＋ 明確 negative trigger**，且 negative trigger 直接點名「review skill」把責任交棒給 `code-review`。 |
| `code-review:review-forge` | 「Use when orchestrating a code review workflow across multiple LLMs or agents, synthesizing review findings, cross-voting...」（來源：`plugins/code-review/skills/review-forge/SKILL.md`） | 沒有寫 negative trigger 排除 `verification-gate`，消歧責任單向落在後者身上（見下）。 |
| `code-review:verification-gate` | 「Use after code is written, when a change needs verifiable evidence instead of a claim that it works... Use when the user asks to verify, prove, gate, or hand off finished work... **Not a code review skill — it does not read code looking for defects.**」（來源：`plugins/code-review/skills/verification-gate/SKILL.md`） | 單句 negative trigger 直接排除自己跟 `review-forge` 的重疊，是本 repo 現有 skill 中「一句話消歧」的最佳範例。 |
| `advisor:orchestration` | 「Architect-as-orchestrator routing doctrine... **USE WHEN** delegating implementation work to grok-implementer or codex-implementer, writing a spec for a subagent, consulting claude-advisor at a commitment boundary, or managing session cost and token spend.」（來源：`plugins/advisor/skills/orchestration/SKILL.md`） | 用大寫「USE WHEN」＋條列具體情境，觸發面聚焦在「委派/架構師模式」，與其他 skill 語意重疊度低。 |
| `slim-agents-md` | 中文條列「觸發情境：(1) 指令文件過長...(2) 文件內規則互相矛盾...(3) AGENTS.md 與 CLAUDE.md 並存且內容漂移...(4) 使用者要求『重構／精簡／整理 AGENTS.md 或 CLAUDE.md』...」（來源：`plugins/slim-agents-md/skills/slim-agents-md/SKILL.md`） | 觸發詞聚焦在「精簡/重構指令文件」，與 7 個外部套件完全無重疊（唯一與外部套件語意零碰撞的 in-house skill）。 |

**小結**：本 repo 自己的 6 個 skill 之中已有 3 個用了某種形式的明確消歧（觸發詞列表、negative trigger、大寫 USE WHEN），只有 `review-forge` ↔ `verification-gate` 這一組是單向消歧（只有後者排除前者，前者沒有反向排除）——技術上仍可能被使用者一句籠統的「review 一下」同時命中兩者，只是 `verification-gate` 的自我排除降低了誤觸發機率。

---

## 5. Router 設計選項評估與建議

### 5.1 (a) 專用 router／「start」skill ＋ 決策表

**運作機制（文件明載）**：一個獨立的 skill（例如 `name: which-skill` 或 `name: start`），其 `description` 寫成「Use at the start of any session involving design/visualization/review work in this repo — routes to the correct installed skill among 11+ overlapping packages」，本體是第 2 節手法的綜合體：情境 → skill 名稱的表格 ＋ 一條 tie-break 規則。

**成本與行為（依 1.1.2、1.1.4 節文件機制推導）**：
- 平時只有 `name` + `description` 進 listing，佔用前述「1% context window」預算裡的一小份（跟其他 32 個 skill 一樣付「listing 稅」，但只有一份，不會疊加）。
- 被觸發時本體全文載入，之後常駐 context 直到下一次 compaction；因此 router 本體應遵循 `code.claude.com/docs/en/skills` 的建議「Keep the body itself concise... every line is a recurring token cost」——決策表要短，不要把下游 11 個套件的用法也寫進來。
- **殘餘風險（推論）**：router 只是「多一個候選項」，它自己也要在 listing 裡跟其他 32 個 skill 競爭「被選中」——如果使用者的 prompt 已經精準到直接命中某個 leaf skill（例如明講「brutalist」），router 未必會被優先觸發，此時 router 不介入也不會造成傷害（leaf skill 本來就選對了）；只有在 prompt 含糊（例如「幫我設計」）時，router 才是真正解決衝突的角色，而這正是第 3.8 節衝突矩陣列出的高風險場景。
- **Codex 可攜性**：Codex 用同一份 `SKILL.md` 格式與相同的「先載 name+description、選中才載全文」progressive disclosure（2%／8,000 字元預算），router 模式在 Codex 上機制相通，**但**若要讓同一個 router 檔案同時服務 `claude` 與 `codex` 兩個 output target（`apm.yml` 的 `outputs.codex` 目前已存在、只是註解關閉），frontmatter 應只用 `agentskills.io` 規格相容欄位（`name`／`description`／`license`／`compatibility`／`metadata`／`allowed-tools`），避免用到 Claude Code 專屬欄位（`when_to_use`／`disable-model-invocation`／`user-invocable`等）——這是文件明載的「Using skill frontmatter outside Claude Code」相容表格直接推導出的具體限制。
- **OpenCode 可攜性**：OpenCode 的 skill 發現機制是原生 `skill` 工具＋描述列表，同一份 router `SKILL.md` 放進 `.opencode/skills/` 一樣能被發現，但本次檢索**未查得** OpenCode 端是否也有 listing 預算/截斷機制（見 1.4 節文件缺口）——router 在 OpenCode 上「省 token」的效果無法比照 Claude Code／Codex 精確主張，只能主張「至少提供語意指引」，此為推論而非文件保證。

### 5.2 (b) CLAUDE.md／`.claude/rules/` 路由規則 —— 不建議

依第 1.1.7 節文件明載的結論：`.claude/rules/`（無 `paths:` 限定時）與 `CLAUDE.md` 一樣「every session」載入，跟 skill「只在被選中時才載入本體」的機制正好相反。把一份 11+ 套件、32 個 skill 的決策表放進 CLAUDE.md/rules，等於是把 progressive disclosure 想解決的問題，原封不動地搬回「每次請求都要付費」的那一層——這與本 repo 自己的 `slim-agents-md` skill 想解決的問題（instruction budget、token 每次都被載入的代價，見 `docs/research/agents-md-refactoring.md` 第 1.3(a) 節）直接矛盾，**不建議**採用此方案作為主要機制。唯一合理的殘餘用途（推論）：在 CLAUDE.md 留一句極短指標，例如「設計/視覺化相關請求請先確認是否該用 `which-skill` router」，把路由邏輯本身仍然放在 skill 裡、CLAUDE.md 只留一行指向它——這其實是方案 (a) 的輔助，不是獨立方案。

### 5.3 (c) `UserPromptSubmit` hook —— 不建議作為主要機制

依第 1.1.7 節：官方文件未把此 hook 描述為路由機制，其設計用途是在「模型看到 prompt 之前」做關鍵字比對/攔截。若要用它做路由，必須自己寫腳本做關鍵字匹配，這是**確定性規則**，語意涵蓋能力天生弱於「把良好措辭的 `description` 直接交給模型做語意判斷」——尤其本 repo 目前使用者常用中文（繁體）與英文混合措辭，關鍵字規則的維護成本會很高，且此機制是 Claude Code 專屬（Codex／OpenCode 文件皆未提及對等物），與本 repo「三平台通用」的定位（`README.md` 明言支援 Claude Code / Codex / OpenCode）不符。**推論**：僅建議在極少數「高風險、一旦選錯會執行破壞性操作」的情境下，用 hook 做**攔截／確認**而非「選擇」，例如避免自動觸發某個會直接寫檔或呼叫外部 API 的 skill——但目前 7 個外部套件皆未涉及此類高風險操作，本階段不建議投入。

### 5.4 (d) 描述銳化（sharpening）—— 對 pinned 外部套件不可行，對 in-house 部分可行

依 README.md 與 marketplace.json 記載，7 個外部套件是以 `source: url`／`git-subdir` ＋ pinned `ref`/`sha` 方式轉發，本 repo「不散布這些套件的程式碼」，故**無法直接編輯**其 `SKILL.md`（若編輯，等於 fork 出一份與 upstream 脫鉤的副本，違背「以 commit sha 鎖定版本、由使用者端自 upstream 取得」的既有設計原則，見 `README.md`「授權說明」段）。可行的替代路徑：

1. **對本 repo 自己的 4 個 in-house 插件**：直接應用第 3.6 節、第 4 節觀察到的手法（雙向 negative trigger、明確觸發詞列表），把 `review-forge` 也補上一句排除 `verification-gate` 的反向聲明，讓 in-house 6 個 skill 之間的消歧從「單向」變「雙向」。
2. **對 7 個外部套件**：描述銳化做不到，但方案 (a) 的 router skill 本質上就是「把銳化後的觸發判斷寫在一個本 repo 能控制的檔案裡，一次涵蓋所有下游 skill」——即在「無法改動下游」的約束下，把銳化技巧搬到上游的一個新檔案。這是本研究認為方案 (a) 優先於逐一游說上游修改描述的根本原因：**上游 PR 是長期選項（可對 taste-skill／web-quality-skills 這類內部已有明顯重疊的套件提交 issue/PR，例如替 `taste-skill` 的 13 個子 skill 之間補上像 `plan-preview`/`reviewable-design-doc` 那樣的雙向 negative trigger），但生效時間不可控，且不受本 repo 掌控**。
3. **Marketplace 入口層級的策展（curation）——本 repo 身為 marketplace 維護者唯一能用、且不改上游檔案的官方機制**（`skillOverrides` 對 plugin skill 無效，見 1.1.3 節）。依 `code.claude.com/docs/en/plugin-marketplaces`「Optional plugin fields」「Strict mode」：
   - `strict: true`（預設）：「`plugin.json` is the authority. The marketplace entry can supplement it with additional components, and both sources are merged.」——入口可**加**`skills`／`hooks`（`hooks` 接受 inline object，不需上游有檔案），但**不能減**。
   - `strict: false`：「The marketplace entry is the entire definition. If the plugin also has a `plugin.json` that declares components, that's a conflict and the plugin fails to load.」——入口可**只挑選**上游 `skills/` 的子集合曝光。`taste-skill` 的 `plugin.json`（pinned sha）只有 metadata、未宣告任何 component，符合前提；因此可在 `.claude-plugin/marketplace.json` 對 `taste-skill` 設 `strict: false` 並列出例如 `./skills/taste-skill`、`./skills/brutalist-skill`、`./skills/minimalist-skill`、`./skills/soft-skill`、`./skills/redesign-skill`，把 13 個壓到 5 個，直接減少 listing 預算競爭。**待實測**：(i) 文件的「`skills` adds to the default scan」規則在 `strict: false` 下是否仍會掃描預設 `skills/`（若會，子集合曝光無效）；(ii) `source: url`＋`sha` 的外部來源是否支援 `strict`／`skills` 欄位（文件範例多為 marketplace-root 或 git 來源）。
   - `defaultEnabled: false`（入口欄位，「Takes precedence over the same field in `plugin.json`」）：對低使用率套件（例如 `taste-skill-v1` 若獨立成套件、或整個 `web-quality-skills`）預設安裝即停用，使用者要用再 `/plugin` 開啟——整套件粒度，粗但可用。
   - **識別名副作用（推論，待實測）**：文件在「Path behavior rules」指出，經 `skills` 路徑欄位載入的 skill「takes the skill's invocation name from the frontmatter `name` field… If `name` isn't set… falls back to the directory basename」；而使用者實測預設 `skills/` 掃描下 `taste-skill` 的識別名是目錄名（1.1.6 節）。兩者若同時成立，代表**改用 `strict: false`＋`skills` 路徑後，`taste-skill` 的識別名可能從 `taste-skill:brutalist-skill` 變成 `taste-skill:industrial-brutalist-ui`**——router 決策表必須在切換後重新核對。
   - Codex 側的 `.agents/plugins/marketplace.json` 沒有對等的 `strict`／`skills` 語意，以上僅影響 Claude Code output。
   - **更直接的替代（使用者提出，優於 `strict: false`）：以 `git-subdir` 逐一指向子 skill 目錄，比照 `archify` 目前的做法**。`apm-go marketplace package add <taste-skill.git> --subdir skills/brutalist-skill --name <entry-name> --ref <sha>`；`--subdir` 是單一字串（apm-go 0.3.0-rc.1 `-s, --subdir string`），Claude Code 的 `git-subdir` 來源 `path` 亦為單一字串（文件明載「Required. Subdirectory path within the repo containing the plugin」），因此**一個子 skill = 一個 marketplace 入口**。已確認 `taste-skill` 13 個子 skill 目錄全部自包含（各只有 `SKILL.md`，`stitch-skill` 另有 `DESIGN.md`；`SKILL.md` 內無任何 `../`、`scripts/`、`assets/` 參照），拆出後不會斷鏈。子目錄根層有 `SKILL.md` → Claude Code 依「automatically loaded as a single-skill plugin」規則載入。
     - 優點：不依賴 `strict: false` 的兩個待實測前提；Claude 與 Codex 兩個 output 都支援 `git-subdir`（`archify`、`show-me` 已是先例）；每個子 skill 成為獨立插件，**`/plugin` 與 `defaultEnabled` 的粒度從整套件降到單一 skill**——這正是 `skillOverrides` 對 plugin skill 做不到的事。
     - 代價：N 個入口共用同一 repo/sha（挑 5 個就是 5 筆），升版時 5 筆一起改（`apm-go marketplace outdated`／`check` 可協助）；每筆需自訂 `--name`（例如 `taste-brutalist`），README 表格隨之變長；**授權檔不會跟著子目錄走**（`taste-skill` 的 MIT `LICENSE` 在 repo 根層，與 `show-me` 的缺口相同，README「授權說明」需一併記載）。
     - **識別名待實測**：單一 skill 插件的識別名會是 `<入口名>:<?>`——`archify:archify` 因目錄名與 frontmatter `name` 相同無法區分；`brutalist-skill` 目錄的 `name` 是 `industrial-brutalist-ui`，實際會得到 `taste-brutalist:brutalist-skill` 還是 `taste-brutalist:industrial-brutalist-ui`，需安裝一筆確認後再寫 router 決策表。

### 5.5 建議方案：(a) 為主、(d)-3 為輔、(b)/(c) 不採用

**建議**：在本 repo 新增一個小型 in-house router skill（可作為新插件，例如 `plugins/skills-router`，或掛在既有的某個插件下），具體設計原則：

1. **只用 `agentskills.io` 相容欄位**，讓同一份檔案未來可同時服務 `claude` 與 `codex` 兩個 output target（`apm.yml` 已預留 `outputs.codex`）。
2. **本體極短**（比照 `gitnexus-guide`／`opencli-usage` 的表格密度，避免違反「skill 本體是常駐 context 的固定成本」原則）。
3. **表格用「情境 → 該用的 skill 全名（含 plugin 命名空間）」句型**，並在每一列旁註記「若你已經很確定要哪個風格/子技能，直接講出關鍵字（例如『brutalist』『minimalist』）通常能讓下游套件自己選中對的子 skill，不需要 router 介入」——把 router 定位成「化解模糊，而非取代已經很精準的措辭」。
4. **比照 `spk-meta-skill-map`，補一條 tie-break 規則**：同時符合多列時，依「本 repo in-house 插件優先於外部套件（因為可信賴度與可維護性最高）→ 描述最窄/最精準命中的外部套件優先 → 若仍打平，詢問使用者」的順序處理，而非讓模型自行猜測。
5. **以 marketplace 入口策展（5.4-3 節：`strict: false`＋`skills` 子集合、`defaultEnabled: false`）作為輔助降低 listing 預算競爭**——這是維護者端一次設定、所有使用者受益的做法；`skillOverrides` 對 plugin skill 無效，不可作為建議。

**涵蓋範圍修正（使用者需求）**：router 只涵蓋本 branch 額外加入的 7 個外部套件（26 個 skill 單元），**不涵蓋** in-house 的 4 個插件——後者的 `SKILL.md` 可直接編輯，應改走 5.4 節的描述銳化路線（例如 `verification-gate` 已自帶 negative trigger），不需要 router 代勞。

**兩層路由（使用者需求）**：實際盤點 7 個套件在 pinned sha 上的 `SKILL.md` 後，路由不只是「選哪個 skill」，還有「選中之後要傳什麼參數／模式」——各套件的參數面差異極大：

| 套件 | skill 數 | 第二層的形式 | 來源 |
|---|---|---|---|
| `impeccable` | 1 | **23 個子命令**（6 類）＋ `hooks`／`doctor`／`pin`，另有 4 種 Mode | `skill/SKILL.src.md`「Commands」「Modes」 |
| `taste-skill` | 13 | 無參數；第二層＝**選子 skill**，且目錄名 ≠ frontmatter `name`（例如 `brutalist-skill/` 的 `name` 是 `industrial-brutalist-ui`） | `skills/*/SKILL.md` frontmatter |
| `web-quality-skills` | 6 | 無參數；第二層＝選子 skill | `skills/*/SKILL.md` frontmatter |
| `reviewable-html-workbench` | 3 | 每個 skill 都有 `argument-hint`，含 `--review-mode`／`--preview`／`--output` 旗標 | `skills/*/SKILL.md` frontmatter |
| `archify` | 1 | CLI 子命令：`validate`／`preview`／`visual-check`／`deliver`／`brands [capture <url>]`／`doctor`／`guide`／`demo` | `archify/SKILL.md` 正文的 `node bin/archify.mjs …` 指令 |
| `beautify-github-readme` | 1 | 無參數（正文有「Workflow」章節，依內部流程） | `skills/beautify-github-readme/SKILL.md` |
| `show-me` | 1 | 無參數 | `plugins/show-me/skills/show-me/SKILL.md` |

（以上皆讀自各套件 pinned sha 的實際檔案；`impeccable` 讀到的是建置前模板 `SKILL.src.md`，子命令表本身無佔位符，可視為確定值。）

**特別注意——`impeccable` 上游已內建自己的路由規則**（文件明載，來源：`skill/SKILL.src.md`「Routing」段落）：
- 「**No argument:** read routing.md and present its context-aware menu; **never auto-run a command**.」
- 「**Explicit or clearly implied command:** load its reference … **Ask once if two commands fit**.」
- 「**Otherwise:** treat the request as general design work.」

因此本 repo 的 router 對 `impeccable` 的正確做法是**把使用者意圖翻譯成明確的子命令再交給它**（讓它走第二條規則），而不是不帶參數丟過去（會觸發第一條規則的互動式選單，多一輪往返）。這是「第二層路由」存在的直接理由。

**Router 決策表內容草案 v2**（草案，供撰寫實際 SKILL.md 時參考，非最終文字）：

*第一層：使用者意圖 → 套件*

| 使用者意圖 | 套件 | 進入第二層 |
|---|---|---|
| 前端介面的 UX／UI 設計、審查、打磨、修正（網站、dashboard、product UI、表單…） | `impeccable` | 是，選子命令（見下表 A） |
| 全站／整頁高端視覺風格重做，且講出美學關鍵字（brutalist／minimalist／soft／awwwards／anti-slop） | `taste-*`（方案 A 拆為 5 個入口） | 是，選入口（見下表 B） |
| GitHub README／專案首頁視覺資產（hero、badge、SVG、GIF） | `beautify-github-readme` | 否 |
| 正式的架構／流程／序列／資料流／生命週期圖，需驗證、可匯出 | `archify` | 是，選子命令（見下表 D） |
| 對話中快速畫個簡圖幫助理解，不需正式交付物 | `show-me` | 否 |
| 可在瀏覽器留言討論的設計文件、Plan Mode 預覽、HTML 報告渲染 | `reviewable-html-workbench` | 是，選子 skill ＋ 旗標（見下表 C） |
| 網站效能／無障礙／SEO／最佳實務稽核（非 UI 設計本身） | `web-quality-skills` | 是，選子 skill（見下表 E） |

Tie-break（同時命中兩套件時）：`beautify-github-readme` 受詞含 README → 優先；`impeccable` vs `taste-skill` → 有美學關鍵字選 `taste-skill`，否則 `impeccable`；`archify` vs `show-me` → 提到「交付／匯出／驗證」選 `archify`，否則 `show-me`；仍打平 → 詢問使用者。

*第二層 A：`impeccable` 子命令*（依上游 6 個分類；`[target]` 為選填的檔案或路由）

| 使用者意圖 | 傳入子命令 |
|---|---|
| 首次導入、建立產品脈絡 PRODUCT.md | `init`（`teach` 為別名） |
| 從既有程式碼產生 DESIGN.md | `document` |
| 抽出可重用 tokens／components 成 design system | `extract [target]` |
| 動手寫碼前先規劃 UX／UI | `shape [feature]` |
| UX 設計審查、要評分 | `critique [target]` |
| UI 技術品質檢查（a11y／效能／響應式）——**限單一 UI 目標**；整站稽核改走 `web-quality-skills` | `audit [target]` |
| 出貨前最後打磨 | `polish [target]` |
| 視覺太保守／太吵／太複雜／要衝破常規 | `bolder`／`quieter`／`distill`／`overdrive [target]` |
| 生產就緒：錯誤狀態、i18n、邊界情況 | `harden [target]` |
| 首次使用流程、空狀態、啟用 | `onboard [target]` |
| 動效／色彩／字體／版面／趣味細節 | `animate`／`colorize`／`typeset`／`layout`／`delight [target]` |
| UX 文案／多裝置適配／UI 效能診斷 | `clarify`／`adapt`／`optimize [target]` |
| 在瀏覽器即時挑元素產生變體 | `live` |
| 開關設計檢測 hook、修復產物漂移 | `hooks <on\|off\|status\|…>`／`doctor` |
| 使用者意圖籠統、無法對應任一子命令 | **不帶參數**（讓上游呈現選單） |

*第二層 B：`taste-*` 入口*（無參數；**已依方案 A 落地**：`taste-skill` 改以 `git-subdir` 拆成 5 個獨立入口，其餘 8 個子 skill 未收錄。每個入口是「根層即 `SKILL.md`」的單一 skill 插件，識別名在目錄名 ≠ frontmatter `name` 時取何者**待實測**，下表兩個候選並列）

| 使用者意圖 | marketplace 入口（`--subdir`） | router 引用候選（待實測擇一） |
|---|---|---|
| 預設高端前端品味（無特定風格詞） | `taste-skill`（`skills/taste-skill`） | `taste-skill:taste-skill` 或 `taste-skill:design-taste-frontend` |
| 粗獷／工業風 | `taste-brutalist`（`skills/brutalist-skill`） | `taste-brutalist:brutalist-skill` 或 `taste-brutalist:industrial-brutalist-ui` |
| 極簡 | `taste-minimalist`（`skills/minimalist-skill`） | `taste-minimalist:minimalist-skill` 或 `taste-minimalist:minimalist-ui` |
| 柔和高端／awwwards 等級 | `taste-soft`（`skills/soft-skill`） | `taste-soft:soft-skill` 或 `taste-soft:high-end-visual-design` |
| 既有專案升級到 premium（audit → redesign） | `taste-redesign`（`skills/redesign-skill`） | `taste-redesign:redesign-skill` 或 `taste-redesign:redesign-existing-projects` |

未收錄（方案 A，目前使用機會低）：`gpt-tasteskill`、`image-to-code-skill`、`imagegen-frontend-web`、`imagegen-frontend-mobile`、`brandkit`、`stitch-skill`、`output-skill`、`taste-skill-v1`。需要時以同樣方式各加一筆入口即可。

*第二層 C：`reviewable-html-workbench` 子 skill 與旗標*（直接取自各 skill 的 `argument-hint`）

| 使用者意圖 | 子 skill | 參數 |
|---|---|---|
| 可留言討論的設計文件 | `reviewable-design-doc` | `[設計對象或 document-model.json] [--review-mode standalone\|review-server] [--preview auto\|tailscale\|local\|off]` |
| Plan Mode 計畫預覽 | `plan-preview` | `[plan-preview-payload.json]` |
| 已有 document-model，只要渲染成 HTML | `visual-html-renderer` | `[document-model.json] [--output output/<date>_<slug>] [--preview auto\|tailscale\|local\|off]` |

*第二層 D：`archify` 子命令*（正文指令；典型流程為 validate → preview → visual-check → deliver）

| 使用者意圖 | 子命令 |
|---|---|
| 檢查 JSON-IR 是否合法 | `validate [workflow]` |
| 本機預覽 | `preview` |
| 視覺回歸檢查 | `visual-check` |
| 正式交付（匯出） | `deliver` |
| 查／擷取品牌圖示 | `brands`／`brands capture <url>` |
| 環境診斷／內建指南／示範 | `doctor`／`guide`／`demo` |

*第二層 E：`web-quality-skills` 子 skill*（無參數）

| 使用者意圖 | 子 skill |
|---|---|
| 整站稽核、或使用者只說「幫我看看網站」 | `web-quality-audit`（總入口） |
| 明確只問單一面向 | `accessibility`／`performance`／`core-web-vitals`／`seo`／`best-practices` |

---

### 5.6 補充：router skill 與 SessionStart hook 的真實取捨，以及混合式方案

使用者提出「router 寫成 skill 可攜但多一次呼叫；用 SessionStart hook 注入省一次呼叫但各 harness 設定不同」。對照文件後，兩邊各有更關鍵的因素：

**Router skill 的真正弱點不是多一次呼叫，而是它自己也在同一場 description 抽籤裡**（推論）：router 只在模型「先選中 router」時才有作用，而這個決定與選中 `impeccable` 是同一種語意比對；`impeccable` 的 description 列了 15 個動詞、涵蓋所有前端介面，模型很可能直接命中它。又因 `skillOverrides` 對 plugin skill 無效（1.1.3 節），**無法**把 26 個外部 skill 降為 name-only 讓 router 成為唯一語意入口；能做的只有 5.4-3 節的入口策展（減少競爭者數量）與下述的常駐 pointer（提高 router 被優先採用的機率）。

**SessionStart hook 有兩個文件明載的優點**（來源：`code.claude.com/docs/en/hooks`）：
- stdout 直接成為 Claude 可見的 context：「The exceptions are `UserPromptSubmit`, `UserPromptExpansion`, `SessionStart`, and `PostModelSwitch`, where Claude Code adds plain-text stdout as context that Claude can see and act on.」
- matcher 含 `compact`（`startup`／`resume`／`clear`／`compact`／`fork`），亦即 **compaction 後會重新注入**；相對地 skill 本體在 compaction 後只靠 1.1.4 節的「每個 skill 前 5,000 tokens、合計 25,000 tokens」預算回填。
- 另一個推論優點：hook 是腳本，可掃描 `~/.claude/plugins/cache/` 實際安裝的 SKILL.md frontmatter**動態產生**第一層表格，pin 升版自動跟上；靜態 router skill 會過期（`impeccable` 的子命令跨版本已有變動：`live`／`shape` 新增、`craft` 棄用）。
- 缺點：每個 session 固定成本（與否決 (b) 的理由相同），且 Claude Code 專屬——Codex／OpenCode 無對等機制（1.1.7 節）。Claude Code 插件可用 `hooks/hooks.json` 或 marketplace 入口的 inline `hooks` 攜帶。

**兩層路由的成本結構不同，不該用同一種機制**：第一層（意圖 → 套件）7 列、約 30 tokens，常駐注入負擔得起；第二層（`impeccable` 23 個子命令、`taste-skill` 13 個子 skill…）只能放 skill 本體，且 `impeccable` 自帶 `routing.md`，本 repo 只需「意圖翻譯成子命令」。

**建議：混合式**
1. Router skill 持有完整兩層表格（Agent Skills 規格、可攜、progressive disclosure；可用 `skill-creator` 評測觸發準確度，hook 無此工具）。
2. 每個 host 一行常駐 pointer：Claude Code 用 router 插件自帶的 SessionStart hook（例如「設計／圖表／文件審閱／網站品質類任務，先呼叫 `skills-router`」，compaction 後自動重注入）；Codex／OpenCode 用 AGENTS.md 同一句話。與本 repo `slim-agents-md` 的原則一致：根層只放 pointer，細節在 skill。
3. 維護者端以 5.4-3 節的入口策展減少競爭者（`taste-skill` 子集合、低使用率套件 `defaultEnabled: false`）。

## 6. 引用來源總表

| Claim | 來源 |
|---|---|
| `description`/`when_to_use` 是模型決定是否觸發 skill 的唯一語意欄位；`argument-hint`/`allowed-tools` 不影響選擇 | `code.claude.com/docs/en/skills`（frontmatter 參照表） |
| description+when_to_use 於 listing 中截斷於 1,536 字元；`skillListingMaxDescChars` 可調 | `code.claude.com/docs/en/skills`「Skill descriptions are cut short」 |
| listing 字元預算＝模型 context window 的 1%（`skillListingBudgetFraction` 可調）；超量時砍最少被呼叫的 skill 描述 | `code.claude.com/docs/en/skills`，同上段 |
| `disable-model-invocation`／`user-invocable` 兩軸矩陣 | `code.claude.com/docs/en/skills`「Control who invokes a skill」 |
| `skillOverrides` 四狀態（on/name-only/user-invocable-only/off） | `code.claude.com/docs/en/skills`「Override skill visibility from settings」 |
| Skill 內容進 context 後常駐；compaction 後每個 skill 保留前 5,000 token、總預算 25,000 token | `code.claude.com/docs/en/skills`「Skill content lifecycle」 |
| `skill-creator` 官方外掛的 eval 流程（should-trigger/should-not-trigger、benchmark.json） | `code.claude.com/docs/en/skills`「Evaluate and iterate on a skill」 |
| `claude plugin validate` 檢查 manifest schema／agent frontmatter；未提及 `claude plugin eval` 或 `/skill-doctor` | `code.claude.com/docs/en/plugins-reference`（WebFetch 檢索確認查無） |
| Plugin skill 命名空間 `plugin-name:skill-name` | `code.claude.com/docs/en/skills`「Where skills live」；`code.claude.com/docs/en/plugins` |
| `UserPromptSubmit` hook 不影響 skill 選擇，運作於 prompt 處理之前 | `code.claude.com/docs/en/hooks`（WebFetch 摘要） |
| `.claude/rules/` 每個 session 都載入，官方建議路由/任務型指令改用 skill | `code.claude.com/docs/en/memory`「Organize rules with `.claude/rules/`」提示框 |
| SKILL.md frontmatter 規格：`name`（≤64 字元）、`description`（≤1024 字元）、progressive disclosure 三階段 | `agentskills.io/specification` |
| description 好/壞範例、「keywords that help agents identify relevant tasks」 | `agentskills.io/specification`「description field」 |
| Agent Skills 為 Anthropic 發起的開放格式，40+ client 採用 | `agentskills.io`（client showcase） |
| Codex `docs/skills.md` 轉介至官方文件頁 | `github.com/openai/codex/blob/main/docs/skills.md`（pinned 讀取） |
| Codex `description` 定位為「Defines when the skill should/shouldn't trigger」；`$skill-name` 顯式呼叫；隱式匹配；掃描路徑順序 | `learn.chatgpt.com/docs/build-skills`（`developers.openai.com/codex/skills` 308 導向） |
| Codex progressive disclosure：listing 上限 2% context window 或 8,000 字元 | 同上 |
| OpenCode SKILL.md 搜尋路徑、`name`/`description` 約束、原生 `skill` 工具呼叫機制 | `opencode.ai/docs/skills/` |
| OpenCode 管理員 `allow`/`deny`/`ask` 權限規則 | `opencode.ai/docs/skills/` |
| `opencli-usage` 的「Where to go next」表格 | 本機 `~/.claude/skills/opencli-usage/SKILL.md` |
| `spk-start-here` 分層路由 ＋ 明確 fallback（`spk-meta-skill-map`） | 本機 `~/.claude/skills/spk-start-here/SKILL.md` |
| `spk-meta-skill-map` 命名慣例＋衝突 tie-break 規則（「narrowest matching skill」「earliest lifecycle family」） | 本機 `~/.claude/skills/spk-meta-skill-map/SKILL.md` |
| `spk-start-command-map` 命令 vs 操作指南邊界聲明 | 本機 `~/.claude/skills/spk-start-command-map/SKILL.md` |
| `gitnexus-guide`「Always Start Here」＋任務表 | 本機 `~/.claude/skills/gitnexus-guide/SKILL.md` |
| `web-quality-skills` 6 個子 skill 描述與觸發詞 | `addyosmani/web-quality-skills`，`ref=afa8da942115f2961fdbfa80807ea0b232ff6c00` |
| `impeccable` SKILL.src.md 完整 frontmatter、「Modes」「Commands」（23 個子命令）與「Routing」段落 | `pbakaus/impeccable`，`ref=63b04e2530f5c7b41ea83c133daab24f34912456` |
| `taste-skill` 13 個子 skill 清單與各自 frontmatter | `Leonxlnx/taste-skill`，`ref=ccbc15639c97057cbfcf32ecebc38ef716e4bb37` |
| `beautify-github-readme` frontmatter | `oil-oil/beautify-github-readme`，`ref=55bdb1c05414cd7a0cf911d02e55ece79777206e` |
| `show-me` frontmatter | `humanlayer/skills`，`ref=3c2629142c5d437428269b1b722b08c0b87f574d`，`subdir=plugins/show-me` |
| `reviewable-html-workbench` 3 個 skill 的雙語 negative trigger 與各自 `argument-hint` | `u-ichi/reviewable-html-workbench`，`ref=2be05dbd31510670af04381e24d735c4c77493b8` |
| `archify` frontmatter、內建「Type router」表與正文 CLI 子命令（`validate`/`preview`/`visual-check`/`deliver`/`brands`…） | `tt-a1i/archify`，`ref=c826e6c3a7abad19c0f3cd1ca57207d54b1ad8de`，`subdir=archify` |
| 本 repo 4 個 in-house 插件的 SKILL.md 觸發面 | `plugins/{git-assistant,advisor,code-review,slim-agents-md}/skills/*/SKILL.md` |
| `apm.yml`／`.claude-plugin/marketplace.json`／`.agents/plugins/marketplace.json`／`README.md` 的套件清單、來源、版本鎖定與授權說明 | 本 repo 根目錄對應檔案 |
| `.claude/rules/`／CLAUDE.md 指令預算代價的既有分析（用於否決方案 (b)） | `docs/research/agents-md-refactoring.md`（本 repo既有研究筆記） |
| `anthropics/skills` template 最小 `SKILL.md` 範例 | `github.com/anthropics/skills`，`template/SKILL.md` |
| `skillOverrides` 不適用於 plugin skill；`/plugin` 僅能整套件停用 | `code.claude.com/docs/en/skills`「Override skill visibility from settings」「Disable a skill」 |
| Marketplace 入口的 `strict`／`skills`／`hooks`／`defaultEnabled` 欄位與 Strict mode 語意 | `code.claude.com/docs/en/plugin-marketplaces`「Optional plugin fields」「Strict mode」 |
| `skills` 路徑欄位「adds to default scan」規則、經路徑欄位載入的 skill 以 frontmatter `name` 為識別名 | `code.claude.com/docs/en/plugins-reference`「Path behavior rules」 |
| SessionStart hook stdout 進入 context；matcher 含 `compact`；resume/fork 重跑 | `code.claude.com/docs/en/hooks`「Hook output」「SessionStart」 |
| `taste-skill` 的 `plugin.json` 僅含 metadata、未宣告 component（`strict: false` 前提） | `Leonxlnx/taste-skill`，`.claude-plugin/plugin.json`，`ref=ccbc15639c97057cbfcf32ecebc38ef716e4bb37` |

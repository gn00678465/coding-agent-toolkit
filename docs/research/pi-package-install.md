# 研究筆記：讓本專案的 plugin 可以用 Pi 安裝

- **問題**：Pi coding agent 有沒有類似 Claude Code / Codex 的 marketplace？本專案的 plugin 要怎麼調整，才能用 `pi install` 安裝？
- **等待這個答案的決策**：plugin 要加哪些檔案，先從 `git-assistant` 開始。
- **版本**：Pi 1.4.0（`@earendil-works/pi-coding-agent`）。原始碼讀的是 `earendil-works/pi` 的 commit `42cb822f1c5d3153069dd0661bfd297424666cf1`。
- **研究方式**：Pi 沒有 subagent，所以沒有交給 `researcher` 背景代理，改由主 session 自己讀官方文件和原始碼，再用隔離專案實測。

---

## 1. 結論

1. **Pi 沒有 marketplace。** 沒有類似 `.claude-plugin/marketplace.json` 的目錄檔，也沒有「一個來源列出多個 plugin」的機制。Pi 的分發單位是 **package**，來源有三種：npm、git、本機路徑。最接近 marketplace 的是 [Pi package gallery](https://pi.dev/packages)，但它只收錄有 `pi-package` keyword 的 **npm** 套件（`docs/packages.md`）。
2. **git 來源不能指定子目錄。** `parseGitUrl` 只解析 host、`user/project` 和 ref（`src/utils/git.ts:172-226`），整個 repo 就是一個 package。所以從 GitHub 安裝時，`plugins/git-assistant/` 不能單獨當成一個來源。
3. **package 如何找到資源**（`src/core/package-manager.ts:2241-2270`）：
   - package 根目錄的 `package.json` 有 `pi` 欄位時，**只**載入 `pi.skills`、`pi.prompts`、`pi.extensions`、`pi.themes` 列出的路徑。
   - 沒有 `pi` 欄位時，改用慣例目錄：根目錄的 `skills/`、`prompts/`、`extensions/`、`themes/`。
   - 本專案根目錄沒有這些目錄，所以在加入 `package.json` 之前，`pi install git:github.com/gn00678465/coding-agent-toolkit` 什麼都載入不到。
4. **使用者可以篩選要載入的資源。** settings 的物件形式支援 `skills`、`prompts` 等 glob 篩選，可以用 `!` 排除、`+` 強制納入、`-` 強制排除（`docs/packages.md`「Select package resources」、`package-manager.ts:751`）。repo 之後收錄多個 plugin 時，使用者靠這個只啟用需要的部分。
5. **git 安裝會跑 npm install。** clone 之後，只要有 `package.json` 就會執行一次 npm install（`package-manager.ts:1920-1923`）。本專案的 `package.json` 沒有 dependencies，所以這一步不會下載任何東西。

## 2. Pi 讀取資源的細節

| 項目 | 行為 | 來源 |
|---|---|---|
| skill | 目錄中的 `SKILL.md`，description 上限 1024 字元，超過只會警告 | `docs/skills.md`、`src/core/skills.ts:13-123` |
| skill 何時出現在 system prompt | 停用 read tool（`--no-tools`）時不會列出 skill | 實測（見第 4 節） |
| prompt template | 檔名去掉 `.md` 就是指令名稱。`gitignore-generator.prompt.md` 會變成 `/gitignore-generator.prompt` | `src/core/prompt-templates.ts:134` |
| prompt frontmatter | 只讀 `description` 和 `argument-hint`，其他欄位（例如 Copilot 的 `agent`）忽略 | `docs/prompt-templates.md` |
| agent / subagent | Pi 沒有 subagent，Claude 的 `agents/*.md` 和 Codex 的 `.codex/agents/*.toml` 都用不到 | `docs/` 沒有 subagent 文件 |
| 專案層級安裝 | 寫到 `.pi/settings.json`，專案要先被信任（`-a` / `--approve`） | `docs/packages.md` |

## 3. git-assistant 的調整

| 檔案 | 用途 |
|---|---|
| `package.json`（repo 根目錄） | 給 `pi install git:github.com/gn00678465/coding-agent-toolkit` 用。`pi` 欄位目前只列 git-assistant 的 skills 和 prompts。設 `private: true`，避免誤發布到 npm |
| `plugins/git-assistant/package.json` | 給本機路徑安裝（`pi install ./plugins/git-assistant`）用，也是之後發布 npm 的基礎。`pi` 欄位明確列出 `./skills` 和 `./prompts/*.prompt.md` |

git-assistant 的兩個 skill（`pull-request`、`issue-template`）沒有用到特定 harness 的工具，description 分別是 616 和 396 字元，都在上限內，所以內容不用修改。

prompt 檔名維持 `.prompt.md`，因為這是 Copilot 和 apm 的命名慣例。Pi 會把指令名稱顯示成 `/gitignore-generator.prompt`。

## 4. 實測（隔離專案，Gemini 3.8 Flash）

| 測試 | 指令 | 結果 |
|---|---|---|
| plugin 目錄 | `pi install -l -a <repo>/plugins/git-assistant` | 載入 `pull-request`、`issue-template`；`/gitignore-generator.prompt` 展開後的內容正確 |
| repo 根目錄（模擬 git 安裝後的內容） | `pi install -l -a <repo>` | 只載入 git-assistant 的兩個 skill 和一個 prompt，沒有載入其他 plugin |
| `pi -e <plugin 目錄>` | `-e` 是載入 extension 用的，不適合載入 skill package | 沒有載入任何 skill |

尚未驗證：還沒推送到 GitHub，所以沒有實際跑 `pi install git:github.com/gn00678465/coding-agent-toolkit`。clone 下來的內容和本機根目錄相同，資源怎麼被找到應該一致，但 npm install 那一步沒有測。

## 5. pstack、impeccable、ui-design

### 5.1 外部套件不能透過本專案的 package 轉發

本專案只保存外部套件的 URL 和 commit sha，不散布它們的檔案。Pi 的 package 只能載入自己目錄內的檔案，所以根目錄 `package.json` 沒辦法直接指向外部套件。我試過用 npm 的 git dependency 間接引入，兩個都不可行：

| 套件 | 嘗試 | 結果 |
|---|---|---|
| pstack（`cursor/plugins` 的子目錄） | `npm install github:cursor/plugins#<sha>` | 失敗：上游根目錄沒有 `package.json`（`ENOENT: Could not read package.json`） |
| impeccable | `npm install github:pbakaus/impeccable#<sha>` | 裝得起來，但花了約 2 分鐘，而且 npm 依上游 `package.json` 的 `files`（只有 `cli/bin/`、`LICENSE`）打包，`.pi/skills/` 不在裡面 |

直接用 `pi install git:...` 安裝上游 repo 也不行：兩個上游都沒有 `pi` 設定，根目錄也沒有 `skills/`，裝了什麼都不會載入。

### 5.2 可行做法（已實測）

| 套件 | 做法 | 實測結果 |
|---|---|---|
| impeccable | 官方安裝程式 `npx impeccable install --providers=pi --scope=project|global`，會寫到 `.pi/skills/impeccable` 或 `~/.pi/agent/skills/impeccable`（impeccable `crates/skills/src/providers.rs`） | skill 出現在 available skills 中 |
| pstack | `pi install git:github.com/cursor/plugins@<sha>`，再在 settings 的 `skills` 加上 `git/github.com/cursor/plugins/pstack/skills`。使用者層級的 git 安裝位置是 `~/.pi/agent/git/<host>/<path>`，專案層級是 `.pi/git/<host>/<path>`（`package-manager.ts:2160-2181`） | 57 個 skill 都載入了。其中 56 個有 `disable-model-invocation: true`，只能用 `/skill:<name>` 呼叫；`/skill:architect` 正常展開 |
| ui-design | 根目錄 `package.json` 的 `pi.skills` 加入 `./plugins/ui-design/.apm/skills`（以點開頭的目錄要明確列出） | skill 載入，並在 Pi 上走 inline 模式（見 5.3） |

pstack 的 `recall` 和使用者層級同名的 skill 衝突，Pi 只保留先找到的那一個（`docs/skills.md`）。

### 5.3 ui-design 在 Pi 上的調整與實測

Pi 沒有 subagent，所以 `ui-design` skill 新增 **inline 模式**：在主 session 讀取 `../../agents/impeccable-ui-designer.agent.md`，照 agent 定義執行。原本回報 `NEEDS_DECISION` 的地方改成直接問使用者，也允許在主 session 跑 live / generate。

用 Claude Sonnet 5 在 Pi 上做了三輪實測，每輪都修正一個問題：

| 輪次 | 問題 | 修正 |
|---|---|---|
| 1 | 模型沒有載入 `ui-design`，直接改 CSS（產生一般的預設樣式） | description 改成不綁定 subagent 的說法，並明確納入間距、排版、字體等小型視覺修正 |
| 2 | 載入了 skill，但用 `find /` 搜尋 agent 檔和 impeccable，掛到逾時 | skill 指定從 skill 位置解析路徑、不要搜尋檔案系統；agent 的 preflight 新增 Pi 的 impeccable 位置 |
| 3 | 流程正確：`ui-design` → agent 定義 → `impeccable context` → `layout.md`、`craft-floor.md` → 修改 → `detect`（0 項） | — |

第 3 輪仍有兩點不足：沒有做截圖檢查（環境沒有瀏覽器工具），最後回覆也沒有照固定的報告格式。

Antigravity ACP provider（Gemini）會把工作交給自己的代理執行，不會用到 Pi 的 skill 和工具，所以不適合拿來測 Pi 的 skill。


## 6. Pi 使用外部套件的方式

- **問題**：不把外部套件的檔案複製進本專案，Pi 有沒有辦法使用它們？
- **原始碼版本**：`earendil-works/pi` commit `14c8118412bffc8f8df7a088fde51d2ffa74fd8f`。

### 6.1 可用的機制

| 機制 | 做法 | 適用 | 限制 |
|---|---|---|---|
| A. 各自 `pi install` | 使用者對每個上游各下一次 `pi install` | 上游本身就是 Pi package | impeccable、pstack 都不是（見 5.1） |
| B. 專案 settings 清單 | 把 `packages` 和 `skills` 寫進 `.pi/settings.json` 並 commit，團隊成員信任專案後自動安裝 | 團隊共用一份清單，作用類似 Claude 的 `enabledPlugins` | 仍受 A 的限制。pstack 要搭配 `skills` 路徑（5.2） |
| C. npm dependencies | 在 package 的 `dependencies` 引入其他套件，再用 `node_modules/...` 路徑列出資源（`docs/packages.md`） | 上游有 npm 套件，而且套件裡有 skill 檔 | impeccable 的 npm 套件不含 skill，cursor/plugins 沒有 `package.json`（5.1） |
| D. extension 動態提供資源 | package 內附一個 extension，在 `resources_discover` 事件下載上游的固定版本，再回傳 `skillPaths` / `promptPaths` | 任何 git 上游，可以只取子目錄 | 會執行 extension 程式碼（使用者要信任）；第一次啟動需要網路和 git |

### 6.2 機制 D 的原始碼依據

- `resources_discover` 在 `session_start` 之後觸發，`reason` 是 `startup` 或 `reload`（`src/core/extensions/types.ts:724-736`）。
- handler 可以是 async，回傳的 `skillPaths`、`promptPaths`、`themePaths` 會併入資源，並重建 system prompt（`src/core/agent-session.ts:3344-3366`、`src/core/extensions/runner.ts:1485-1525`）。
- extension 可以用 `pi.exec(command, args, options)` 執行外部指令（`src/core/extensions/types.ts:1767`）。
- 官方範例：`examples/extensions/dynamic-resources/index.ts`。

### 6.3 機制 D 的原型實測

原型是一個 package（`pi.extensions: ["./extensions/upstream.ts"]`），extension 用 `git sparse-checkout` 加上 `fetch --depth 1` 取得上游固定 commit 的子目錄，暫存在 `~/.pi/agent/cache/<package>/<name>-<sha>`，已經下載過就直接沿用。

| 上游 | 取得的子目錄 | 結果 |
|---|---|---|
| pstack（`cursor/plugins@9b93e81`） | `pstack/skills` | 第一次啟動約 31 秒（包含模型回應）。57 個 skill 都載入，`/skill:architect` 正常展開 |
| impeccable（`aeeb3d8`） | `.pi/skills`，另外加上 `--filter=blob:none` | 只用 git 測試：約 2 秒，下載 2.3 MB（repo 總大小約 775 MB）。`scripts/impeccable` 啟動器會在第一次使用時下載 engine（impeccable README） |

這個做法和 Claude / Codex marketplace 的模式相同：本專案只保存 URL 和 sha，檔案在使用者電腦上從上游取得，不違反本專案「不散布外部程式碼」的立場。

### 6.4 若要在本專案實作 D

- **版本來源**：refs 由 `apm.yml` 的 `packages` 管理（每天的 upstream-update workflow 會更新）。extension 不能有 dependencies，沒辦法解析 YAML，所以建議由 script 從 `apm.yml` 產生 `pi-upstreams.json`，記錄 name、repo、ref 和 skill 子目錄，並放進同一個 workflow。
- **每個上游要另外指定 skill 子目錄**：例如 impeccable 是 `.pi/skills`，pstack 是 `pstack/skills`，其他套件要逐一確認。
- **錯誤處理**：clone 失敗只回報錯誤，不能讓整個 Pi 啟動失敗。runner 會捕捉 handler 拋出的例外並發出 extension error（`runner.ts:1508-1520`），所以不會擋住啟動。
- **無法做到的部分**：impeccable 的 Pi 版本沒有 hook（Pi 沒有 hook 介面），和用官方安裝程式的結果相同。

### 6.5 尚未驗證

- extension 放在 git 安裝的 package 中能不能正常載入（原型是用本機路徑安裝）。
- 第二次啟動使用暫存時的速度（預期只會檢查目錄是否存在）。
- `/reload` 是否會重新觸發下載（handler 會先檢查暫存目錄，預期不會重複下載）。

## 7. 第三方 Pi 插件：讀取 Claude / Codex marketplace

- **問題**：有沒有現成的 Pi package，可以直接安裝本專案的 Claude marketplace，包含外部套件？
- **搜尋方式**：用 npm registry 搜尋 `keywords:pi-package` 加上 marketplace、claude plugin、subagent 等關鍵字，時間是 2026-10-23。

### 7.1 候選套件

| 套件 | 版本 | 每月下載 | 用途 | 和本環境相容嗎 |
|---|---|---|---|---|
| `pi-claude-marketplace` | 0.20.1 | 約 11,200 | 讀取 Claude marketplace，支援 commands、skills、agents（需 `pi-subagents`）、hooks（部分）、MCP（需 `pi-mcp-adapter`） | 見 7.2 的實測 |
| `pi-codex-marketplace` | 1.1.0 | 約 900 | 讀取 Codex / Claude marketplace | README 寫明不支援 Windows |
| `@nklisch/pi-plugins` | 0.8.4 | 約 580 | 安裝 Claude / Codex plugin bundle，內建 subagents、MCP | peerDependency 要求 `pi-coding-agent >=0.82.0 <1`，不相容 Pi 1.4.0 |
| `pi-claude-plugins` | 0.2.0 | 約 210 | 從 `~/.claude/plugins/marketplaces` 讀取 Claude Code **已安裝並啟用**的 plugin 的 skills 和 commands | 要先用 Claude Code 安裝 plugin；只支援 skills 和 commands |
| `zmarketplace` | 0.7.8 | — | 跨 agent 搜尋、安裝 plugin | 沒有測試 |

### 7.2 pi-claude-marketplace 實測（專案層級，隔離目錄）

| 測試 | 結果 |
|---|---|
| 用 mise 安裝的 Pi（`pi.exe`，Bun 編譯版本） | **一啟動就當掉**：`proper-lockfile` 在 Bun 下拋出 `TypeError: Proxy handler's 'get' result ...`（`mtime-precision.js:6`） |
| 用 npm 版 Pi（`npx @earendil-works/pi-coding-agent@1.4.0`，Node 執行） | 可以正常載入 |
| marketplace 來源使用 Windows 磁碟路徑（`D:/...`） | `unsupported source`，必須用相對路徑或 GitHub |
| `marketplace add ./mkt`（本專案的副本） | 成功，列出 5 個本專案自己的 plugin |
| 安裝 git-assistant、ui-design | 成功。skill 名稱會加上 plugin 前綴：`git-assistant-pull-request`、`git-assistant-issue-template`，`ui-design` 維持原名 |
| 安裝 pstack（`git-subdir` 來源） | 成功，第一次會 clone `cursor/plugins` |
| 安裝 impeccable（`url` 來源） | 成功，但會 clone 整個 repo，佔用約 670 MB，花了數分鐘 |
| agents | **全部無法使用**：<br>• pstack 的 agent 名稱被改成 `pstack:comment-sicko`，`pi-subagents` 0.81.0 規定 `:` 是保留字元，直接跳過<br>• ui-design 的 agent 根本沒有被轉入：這個插件只讀 `<plugin>/agents/*.md`，不讀 `plugin.json` 的 `agents` 欄位（`bridges/agents/discover.ts`） |

### 7.3 結論

- 有現成插件可以讀取本專案的 Claude marketplace，外部套件也能在使用者電腦上直接從上游取得。但以目前版本來說，**在這台 Windows 上不能直接使用**：
  - Bun 版 Pi 會當掉；
  - 本機磁碟路徑不被支援；
  - agent 有命名衝突，ui-design 的 agent 也不會被讀到。
- 改用 npm 版 Pi 並從 GitHub 加入 marketplace，git-assistant、pstack 和 impeccable 的 skill 就能用。
- 要讓 ui-design 的 agent 能透過這個插件使用，plugin 根目錄要放 `agents/impeccable-ui-designer.md`。Claude Code 本來就會讀這個預設目錄，所以可以拿掉 `plugin.json` 的 `agents` 欄位。這要等 `pi-subagents` 的命名問題解決後才有意義。
- 第 6 節的機制 D（自己寫 extension）不依賴第三方插件，也沒有上面這些相容問題，但要自己維護。

## 8. 方案 D 實作：impeccable 搭配 ui-design

### 8.1 實作

| 檔案 | 內容 |
|---|---|
| `pi/extensions/upstream-skills.ts` | 在 `resources_discover` 讀 `pi/upstreams.json` 和 `.claude-plugin/marketplace.json`，取得 URL、sha 和子目錄。用 `git sparse-checkout --no-cone` 加上 `fetch --depth 1 --filter=blob:none` 下載到暫存目錄，完成後寫入 marker，再 rename 到 `<agent dir>/cache/coding-agent-toolkit/<name>/<sha>`。下載失敗只發 warning，不會擋住 Pi 啟動 |
| `pi/upstreams.json` | 只記錄套件名稱和 skill 目錄。目前只有 `impeccable: [".pi/skills"]` |
| `package.json` | `pi.extensions` 加入上面的 extension |

版本直接讀 apm-go 產生的 `marketplace.json`（JSON），所以不需要另外的產生 script，也不用改 workflow。每天的 upstream-update 更新 sha 後，Pi 下次啟動會改用新的暫存目錄。

### 8.2 實測（隔離專案，Pi 1.4.0 Bun 版本）

| 項目 | 結果 |
|---|---|
| 第一次啟動 | 下載 impeccable 的 `.pi/skills`，暫存約 3.8 MB；`impeccable` 出現在 available skills，路徑指向暫存目錄 |
| 第二次啟動 | 使用暫存，沒有重新下載 |
| `/skill:ui-design <需求>`（Claude Sonnet 5） | 依序：讀 agent 定義 → 讀暫存中的 impeccable `SKILL.md` → `impeccable.cmd context` → reference → 修改 HTML/CSS → `detect` 結果為 `[]` → 用 Playwright 截三種寬度 → 輸出報告 |
| 不加 `/skill:`，直接描述需求 | 3 次測試都沒有載入 skill，模型直接改 CSS。第 5 節的第 3 輪曾成功過一次，所以 Pi 上的自動觸發不穩定 |

### 8.3 發現的問題與修正

- 截圖時，agent 執行了 `pip install pillow`（裝進使用者的 Python），也執行了 `npx playwright install chromium`（裝進使用者的 `ms-playwright` 快取）。兩者都已手動移除。agent 規則改成：只能用已經可用的瀏覽器工具，或把一次性的 driver 套件裝在 OS 暫存目錄；禁止 `pip install`、全域 npm 和 `playwright install`；沒有瀏覽器時就跳過截圖，並回報未驗證。
- agent 仍然執行了一次 `find / -maxdepth 6 -iname impeccable*`，違反「不要搜尋整個檔案系統」的規則，但有 maxdepth 限制，沒有卡住。
- focus 顏色用了 `#2563eb`（Tailwind 預設藍）。原因是專案沒有 PRODUCT.md 或色票，而且報告有揭露。
- `apm-go install` 會把 `.apm/skills/` 複製到 `.agents/skills/` 和 `.claude/skills/`，但不會複製 `.apm/agents/*.agent.md`。agent 會轉成 `.claude/agents/impeccable-ui-designer.md` 和 `.codex/agents/impeccable-ui-designer.toml`。Pi 會自動讀專案的 `.agents/skills/`，所以用 apm-go 裝進專案的 ui-design，原本的相對路徑 `../../agents/impeccable-ui-designer.agent.md` 會找不到檔案。inline 模式改成依序嘗試四個候選路徑：`.apm` 原始檔、`.claude/skills` 旁的 agents、專案根目錄的 `.claude/agents`、`.codex/agents/*.toml`。已在隔離專案（targets claude、codex）用 Pi 驗證，從 `.agents/skills/ui-design` 載入時讀到 `.claude/agents/impeccable-ui-designer.md`。

## 9. 搭配 `@tintinweb/pi-subagents` 執行 subagent

`@tintinweb/pi-subagents`（0.22.0，目前使用者安裝的版本）會讀取已安裝 package 的 `package.json` `pi.subagents.agents`，可以是目錄（非遞迴掃描 `*.md`）或單一檔案。名稱取 frontmatter `name:`，不加前綴，不能含 `:`。根目錄 `package.json` 已加入：

```json
"subagents": { "agents": ["./plugins/ui-design/.apm/agents/impeccable-ui-designer.agent.md"] }
```

`ui-design/SKILL.md` 新增 Pi 列：有這個 extension 且 agent 在可用清單時，用 Agent tool 加 `run_in_background: false` 委派；否則走 inline 模式。

| 測試（隔離的 `PI_CODING_AGENT_DIR`，Claude Sonnet 5） | 結果 |
|---|---|
| package 以 `-l` 裝在專案、信任未儲存（`-a` 不會儲存） | Agent 清單只有 `general-purpose, Explore, Plan`，`ui-design` 走 inline。符合 pi-subagents 文件說的「第一個 session」限制 |
| package 裝在使用者層級 | 清單出現 `impeccable-ui-designer` |
| `/skill:ui-design ...`，SKILL.md 只寫 `run_in_background: false` | 模型沒帶這個參數，agent 在背景執行，print 模式直接結束，沒有改到檔案 |
| 把 `false` 加粗並說明預設是背景 | 主 session 等待 95 秒，subagent 走 `layout` 路線，detector 0 findings，三種寬度截圖，回傳完整報告；主 session 摘要保留假設與揭露 |

剩下的小問題：subagent 在專案根目錄留下一個名為 `nul` 的空檔（Windows 上 bash 的 `2>nul` 導向），也又加了一次 viewport meta（範圍外修改，但有在報告揭露）。這次沒有安裝任何東西到使用者環境。

## 10. 其他本地 plugin

| plugin | Pi 支援 | 說明 |
|---|---|---|
| `code-review` | 加入 `pi.skills` | `review-forge`、`verification-gate` 只需要 skill。`lanes.md` 補上 Pi 的預設 lane（`claude:` + `codex:` CLI），因為 `host` lane 只定義了 Claude Code 與 Codex |
| `slim-agents-md` | 加入 `pi.skills` | 純 skill。AskUserQuestion 在 Pi 不存在，改成對話中詢問 |
| `advisor` | 未加入 | 見下 |

`advisor` 沒有加入的原因：

- skill 名稱 `orchestration` 和使用者已安裝的 Orca `orchestration`（`~/.agents/skills/`）相同。使用者層級的 skill 先被找到，advisor 的會被蓋掉。
- 三個 agent 的 `tools: Read, Grep, Glob` 是 Claude Code 的工具名稱。`@tintinweb/pi-subagents` 只接受 Pi 內建的小寫名稱（`read`、`grep`、`find`…），不認得的名稱會被當成錯誤，agent 拿不到這些工具。同一份檔案無法同時符合兩邊。
- 設計前提是主 session 跑 Claude Fable／Opus 當架構師，`model: fable` 也是 Claude Code 的別名。

已在隔離的 `PI_CODING_AGENT_DIR` 確認 `review-forge`、`verification-gate`、`slim-agents-md` 都出現在 available skills，路徑指向 repo 內的 `plugins/<name>/skills/`。

## 11. SKILL.md 是否符合 Pi 的要求

Pi 的規則（`docs/skills.md`「Write portable frontmatter」）：

- `name` 只能用小寫字母、數字與連字號，不能以連字號開頭或結尾，也不能連續兩個連字號，最多 64 字元。
- `description` 必填，最多 1024 字元。
- 名稱和上層目錄不同時，Pi 不報錯；但其他 Agent Skills 實作可能要求一致。
- frontmatter 格式錯誤或沒有 description 的 skill 不會載入。同名 skill 只保留先找到的那一個，並發出警告。

用腳本逐一解析 frontmatter，結果：

| skill | name 合規 | 與目錄同名 | description 長度 | 規格外欄位 |
|---|---|---|---|---|
| `git-assistant/pull-request` | ✅ | ✅ | 616 | — |
| `git-assistant/issue-template` | ✅ | ✅ | 396 | — |
| `code-review/review-forge` | ✅ | ✅ | 353 | — |
| `code-review/verification-gate` | ✅ | ✅ | 656 | — |
| `slim-agents-md/slim-agents-md` | ✅ | ✅ | 296 | — |
| `ui-design/ui-design`（`.apm/skills`） | ✅ | ✅ | 642 | — |
| `advisor/orchestration` | ✅ | ✅ | 337 | `argument-hint`（Claude Code 用，Pi 忽略） |
| `impeccable`（上游 `.pi/skills`，`aeeb3d8`） | ✅ | ✅ | 約 580 | `version`（Pi 忽略） |

全部符合。實際載入也確認過：在隔離的 `PI_CODING_AGENT_DIR` 執行 `pi install <repo>`，並在 settings 的 `skills` 暫時加入 `plugins/advisor/skills`。上表 8 個 skill 都出現在 available skills，stderr 沒有任何 skill 警告。

advisor 的 `orchestration` 在這次測試中蓋過了使用者 `~/.agents/skills/` 裡的同名 skill：settings 的 `skills` 路徑先被找到。第 10 節的測試中，advisor 不在 package 裡，由使用者層級的那一個勝出。不論哪一個勝出，名稱衝突都存在，所以 advisor 仍列為不支援。

## 12. 對照 issue #33 的「需要調查的問題」

| 問題 | 結論 | 依據 |
|---|---|---|
| pi 如何安裝套件，套件如何宣告資源 | 來源有 npm、git、本機路徑三種。`package.json` 的 `pi` 欄位列出 `extensions`、`skills`、`prompts`、`themes`；沒有這個欄位時讀根目錄的慣例目錄 | 第 1、2 節 |
| 一個 git repo 能否提供多個可分別安裝的 pi 套件 | 不能。git 來源不能指定子目錄，整個 repo 是一個 package。使用者可以用 settings 的篩選只啟用部分資源 | 第 1 節第 2、4 點 |
| 外部套件如何讓 pi 使用者安裝，如何對待「不散布」與授權 | package 內的 extension 在使用者端依鎖定的 commit 從 upstream 下載 skill 目錄，本 repo 不含外部檔案。目前只對 impeccable 啟用 | 第 6、8 節 |
| 版本鎖定（sha、subdir）能否維持 | 能。extension 讀 `.claude-plugin/marketplace.json` 的 `url`、`sha`、`path`，快取目錄以 sha 命名，sha 改變就重新下載 | 第 8 節 |
| 各套件能否在 pi 使用 | git-assistant、code-review、slim-agents-md、ui-design、impeccable 支援。advisor 不支援（第 10、11 節）。其餘外部套件不在這次範圍 | 第 4、8、9、10 節 |
| 各套件的 SKILL.md 是否符合 pi 的要求 | 全部符合 | 第 11 節 |

issue 的「已決定的事項」要求用腳本從 `apm.yml` 產生 pi 的宣告檔。這次沒有做：`package.json` 的 `pi` 欄位與 `pi/upstreams.json` 是手寫的，留給後續 PR。

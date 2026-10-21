# GitHub Issue 模板參考代碼庫 (Production-Ready Templates)

本文件收錄可直接部署至 `.github/ISSUE_TEMPLATE/` 的標準 YAML 範本與中英雙語對照。

---

## 中英雙語欄位與選項對照表

當觸發英文輸出模式時，使用右欄對應文案：

| 欄位 `id` / 項目 | 繁體中文 (預設) | English |
|---|---|---|
| Bug 表單 `name` | `🐛 錯誤回報 (Bug Report)` | `🐛 Bug Report` |
| Bug 表單 `description` | `回報非預期的錯誤行為、崩潰或功能異常（僅需填寫 2 項核心資訊）` | `Report unexpected behavior, crashes, or regressions (only 2 required fields)` |
| `what-happened` label | `問題現象與預期行為 (What happened & Expected behavior)` | `What happened & Expected behavior` |
| `repro` label | `最小重現方式 (Minimal Reproduction)` | `Minimal Reproduction` |
| `code-snippet` label | `觸發錯誤的最小代碼片段 (Minimal Code Snippet)` | `Minimal Code Snippet` |
| `config-file` label | `相關設定檔段落 (Relevant Configuration)` | `Relevant Configuration` |
| `logs` label | `錯誤輸出與堆疊日誌 (Error Output / Stack Trace)` | `Error Output / Stack Trace` |
| `version` label | `軟體與環境版本 (Version & Environment)` | `Version & Environment` |
| `area` label | `受影響的模組區域 (Affected Area)` | `Affected Area` |
| `area` 首項預設值 | `不確定 / 通用 (Not sure)` | `Not sure / General` |
| Feature 表單 `name` | `✨ 功能與強化提案 (Feature Request)` | `✨ Feature Request` |
| Feature 表單 `description` | `提出新功能構想、API 體驗改良或效能強化建議` | `Suggest a new feature, API ergonomic improvement, or performance enhancement` |
| `problem` label | `使用情境與目前痛點 (Use Case & Current Friction)` | `Use Case & Current Friction` |
| `proposal` label | `期望的解決方案或 API 設計 (Proposed Solution)` | `Proposed Solution` |
| `alternatives` label | `替代方案與現有解法 (Alternatives & Workarounds)` | `Alternatives & Workarounds` |
| `contribution` label | `貢獻意願 (Willingness to Contribute)` | `Willingness to Contribute` |
| `contribution` options | `需要維護團隊或社群協助實作` / `願意在維護者指引下嘗試提交 PR` / `已準備好實作並可立即提交 PR` | `Need maintainer or community help to implement` / `Willing to submit a PR with guidance` / `Ready to submit a PR immediately` |
| Docs 表單 `name` | `📖 文件缺漏與修正 (Documentation)` | `📖 Documentation Issue` |
| `doc-issue` label | `文件問題描述 (Issue Description)` | `Documentation Issue Description` |
| `suggestion` label | `建議修正內容 (Suggested Improvement)` | `Suggested Improvement` |

### 設定檔欄位 `render` 語法對照

CLI 範本的 `config-file` 欄位依專案主要設定檔格式填入對應 `render` 值：

| 專案設定檔 | `render` 值 |
|---|---|
| `pyproject.toml`, `Cargo.toml`, `mise.toml` | `toml` |
| `package.json`, `tsconfig.json`, `deno.json` | `json` |
| `*.yml`, `*.yaml` | `yaml` |
| 多格式並存或純文字設定 | `text` |

---

## 1. 入口分流配置檔：`.github/ISSUE_TEMPLATE/config.yml`

> 僅將已啟用的管道列入 `contact_links`；若無任何外部連結，省略整個 `contact_links` 區塊，只保留 `blank_issues_enabled: false`。

```yaml
blank_issues_enabled: false
contact_links:
  - name: 💬 技術問答與使用求助 (Q&A & Discussions)
    url: https://github.com/OWNER/REPO/discussions
    about: 遇到設定疑問、使用方式不確定或想與社群交流？請前往 Discussions 提問，切勿建立 Bug Issue。
  - name: 🔒 資安漏洞私密通報 (Security Vulnerability)
    url: https://github.com/OWNER/REPO/security/advisories/new
    about: 若發現潛在的資安風險，請透過私密管道通報，請勿於公開 Issue 中揭露漏洞細節。
```

---

## 2. 標準通用極簡錯誤回報：`.github/ISSUE_TEMPLATE/1-bug-report.yml`

```yaml
name: 🐛 錯誤回報 (Bug Report)
description: 回報非預期的錯誤行為、崩潰或功能異常（僅需填寫 2 項核心資訊）
title: "[Bug]: "
labels: ["bug"]
body:
  - type: markdown
    attributes:
      value: |
        > 💡 **快速提示**：為節省寶貴時間，本表單僅要求填寫 **2 個必填欄位**。送出前請先透過上方搜尋欄確認是否已有相同回報。

  - type: textarea
    id: what-happened
    attributes:
      label: 問題現象與預期行為 (What happened & Expected behavior)
      description: 請簡述實際發生的錯誤現象，以及原本預期應該出現的正確行為（可直接貼上截圖）。
      placeholder: |
        實際現象：當傳入空陣列時，程式拋出 TypeError 崩潰。
        預期行為：應回傳預設的空物件 `{}` 而不應中斷執行。
    validations:
      required: true

  - type: textarea
    id: repro
    attributes:
      label: 最小重現方式 (Minimal Reproduction)
      description: 請提供以下任一方式協助重現：(1) 幾行可重現的程式碼片段/指令、(2) 簡要操作步驟 1-2-3、或 (3) 線上沙盒 / 最小 Repo 連結。
      placeholder: |
        1. 執行 `my-tool init --empty`
        2. 執行 `my-tool run`
        或直接貼上可重現的最小程式碼片段：
        import { run } from 'my-tool';
        run([]);
    validations:
      required: true

  - type: textarea
    id: logs
    attributes:
      label: 錯誤輸出與堆疊日誌 (Error Output / Stack Trace)
      description: 若有終端機或 Console 錯誤訊息，請直接貼上（系統將自動包裹代碼區塊，無須手動加反引號）。
      placeholder: 請貼上錯誤訊息或 Stack Trace...
      render: text
    validations:
      required: false

  - type: input
    id: version
    attributes:
      label: 軟體與環境版本 (Version & Environment)
      description: 請填入套件版本、執行環境與作業系統（例如 `my-tool --version` 輸出）。
      placeholder: "例如：v1.2.0 / Node.js 22.12.0 / macOS 15.2 (或 Windows 11)"
    validations:
      required: false

  - type: dropdown
    id: area
    attributes:
      label: 受影響的模組區域 (Affected Area)
      description: 若知道問題所屬子系統請協助選擇以加速分流；若不確定請保留預設值。
      options:
        - 不確定 / 通用 (Not sure)
        - 核心引擎 (Core / Runtime)
        - 命令列工具 (CLI / Tooling)
        - 介面與元件 (UI / Components)
        - 建置與設定 (Build / Config)
        - 文件與型別 (Docs / Types)
      default: 0
    validations:
      required: false
```

---

## 3. CLI / 靜態工具極簡貼上回報：`.github/ISSUE_TEMPLATE/1-bug-report.yml`（CLI 變體）

適用於 CLI 工具、套件管理器、編譯器與 Linter（如 Ruff、uv、esbuild 等）：

```yaml
name: 🐛 錯誤回報 (CLI / Tooling Bug Report)
description: 回報命令列工具、解析器或編譯輸出的異常（極簡內嵌重現模式）
title: "[Bug]: "
labels: ["bug"]
body:
  - type: markdown
    attributes:
      value: |
        > 💡 **快速提示**：無須建立外部 Repo，請直接將觸發錯誤的指令、代碼片段與設定檔貼在下方文字框中。

  - type: textarea
    id: what-happened
    attributes:
      label: 錯誤現象與預期行為 (What happened & Expected behavior)
      description: 請簡述執行的命令、實際出現的非預期輸出，以及原本預期的輸出結果。
    validations:
      required: true

  - type: textarea
    id: repro
    attributes:
      label: 觸發錯誤的最小代碼或指令 (Minimal Reproduction Snippet / Command)
      description: 請貼上可直接重現問題的最簡短指令與輸入程式碼片段。
    validations:
      required: true

  - type: textarea
    id: logs
    attributes:
      label: 終端機錯誤輸出 (Terminal Output / Backtrace)
      description: 請貼上完整的錯誤訊息或 stack backtrace（系統自動包裹代碼塊）。
      render: text
    validations:
      required: false

  - type: textarea
    id: config-file
    attributes:
      label: 相關設定檔段落 (Relevant Configuration)
      description: 若問題與設定檔相關，請貼上對應段落（系統自動包裹代碼塊）。
      render: toml
    validations:
      required: false

  - type: input
    id: version
    attributes:
      label: 工具與系統版本 (CLI & OS Version)
      description: 請貼上 `<tool> --version` 輸出與作業系統。
      placeholder: "例如：0.4.15 (Windows 11 x86_64)"
    validations:
      required: false
```

---

## 4. 痛點導向功能提案模板：`.github/ISSUE_TEMPLATE/2-feature-request.yml`

```yaml
name: ✨ 功能與強化提案 (Feature Request)
description: 提出新功能構想、API 體驗改良或效能強化建議
title: "[Feat]: "
labels: ["enhancement"]
body:
  - type: markdown
    attributes:
      value: |
        > 💡 **快速提示**：優秀的功能提案始於清楚的「使用痛點」。若已有類似提案，對該 Issue 按下 👍 (Upvote) 比重複開單更能加速排程！

  - type: textarea
    id: problem
    attributes:
      label: 使用情境與目前痛點 (Use Case & Current Friction)
      description: 請說明這項功能是為了解決什麼實際場景的問題？目前的限制或痛點為何？
      placeholder: "目前在處理批次檔案時，API 僅支援同步單檔讀取，導致必須自行維護外部佇列..."
    validations:
      required: true

  - type: textarea
    id: proposal
    attributes:
      label: 期望的解決方案或 API 設計 (Proposed Solution)
      description: 希望新增什麼樣的功能、設定選項或理想中的呼叫介面？
      placeholder: |
        希望能新增 `batchProcess(files, { concurrency: 4 })` 選項，或支援 AsyncIterable。
    validations:
      required: true

  - type: textarea
    id: alternatives
    attributes:
      label: 替代方案與現有解法 (Alternatives & Workarounds)
      description: 目前是否有暫時的繞道解法（Workaround）？其他類似工具有無可參考的設計？
      placeholder: "目前暫時透過第三方套件封裝處理；可參考某專案的設計..."
    validations:
      required: false

  - type: dropdown
    id: contribution
    attributes:
      label: 貢獻意願 (Willingness to Contribute)
      description: 若維護團隊認可此提案方向，是否有意願協助提交 Pull Request 實作？
      options:
        - 需要維護團隊或社群協助實作
        - 願意在維護者指引下嘗試提交 PR
        - 已準備好實作並可立即提交 PR
      default: 0
    validations:
      required: false
```

---

## 5. 極簡文件修正模板：`.github/ISSUE_TEMPLATE/3-docs.yml`

```yaml
name: 📖 文件缺漏與修正 (Documentation)
description: 回報官方文件、教學範例或型別註解的錯誤或不清楚之處
title: "[Docs]: "
labels: ["documentation"]
body:
  - type: markdown
    attributes:
      value: |
        > 💡 **快速提示**：若為單純的錯別字或小段範例更新，非常歡迎直接提交 Pull Request！

  - type: textarea
    id: doc-issue
    attributes:
      label: 文件問題描述 (Issue Description)
      description: 請說明哪一篇文件、哪個章節有錯誤、缺漏或容易造成誤導之處（請附上文件 URL 或檔案路徑）。
    validations:
      required: true

  - type: textarea
    id: suggestion
    attributes:
      label: 建議修正內容 (Suggested Improvement)
      description: 請提供您認為更正確、更清楚的說明或範例代碼。
    validations:
      required: false
```

---

## 6. 自動化分流工作流範例：`.github/workflows/issue-triage.yml`

> 部署此 workflow 前，請確認對應的 `area:*` 標籤已於儲存庫建立（或由具有 `issues: write` 權限的 `addLabels` 自動附加）。

```yaml
name: Issue Triage Automation

on:
  issues:
    types: [opened]

permissions:
  issues: write

jobs:
  triage:
    runs-on: ubuntu-latest
    steps:
      - name: Auto-assign labels based on Affected Area
        uses: actions/github-script@v7
        with:
          script: |
            const body = context.payload.issue.body || '';
            const match = body.match(/### (?:受影響的模組區域 \(Affected Area\)|Affected Area)\s+([^\r\n]+)/);
            if (!match || !match[1]) return;
            const selectedArea = match[1].trim();
            const labelMap = {
              '核心引擎 (Core / Runtime)': 'area:core',
              'Core / Runtime': 'area:core',
              '命令列工具 (CLI / Tooling)': 'area:cli',
              'CLI / Tooling': 'area:cli',
              '介面與元件 (UI / Components)': 'area:ui',
              'UI / Components': 'area:ui',
              '建置與設定 (Build / Config)': 'area:build',
              'Build / Config': 'area:build',
              '文件與型別 (Docs / Types)': 'documentation',
              'Docs / Types': 'documentation'
            };
            const targetLabel = labelMap[selectedArea];
            if (targetLabel) {
              await github.rest.issues.addLabels({
                owner: context.repo.owner,
                repo: context.repo.repo,
                issue_number: context.payload.issue.number,
                labels: [targetLabel]
              });
            }
```
